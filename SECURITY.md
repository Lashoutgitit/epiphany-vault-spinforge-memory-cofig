# Security Hardening Guide: Epiphany Vault Spinforge Memory Engine

## Overview
This document outlines security best practices for the Epiphany Spin Model v1 FAISS/HNSW memory engine, with specific hardening strategies for edge deployment on Ryzen AI 5 340 hardware.

---

## 1. Infrastructure & Network Security

### API Gateway & Isolation
- **Deploy behind a reverse proxy** (Nginx, HAProxy) with WAF capabilities
- **Zero public IPs on backend memory services** — only expose through API gateway
- **Firewall rules**: Restrict inbound to API gateway IP only

### TLS Configuration
```yaml
# Minimum TLS 1.3 for all traffic
tls_version: "1.3"
ciphers:
  - TLS_AES_256_GCM_SHA384
  - TLS_CHACHA20_POLY1305_SHA256
  - TLS_AES_128_GCM_SHA256
# Disable:
#  - SSL 2.0, 3.0
#  - TLS 1.0, 1.1
#  - RC4, DES, MD5 ciphers
```

### mTLS for Internal Communication
- **Service-to-service**: Enforce mutual TLS between memory engine and API layer
- **Certificate rotation**: 90-day rotations minimum, automated where possible
- **Use SPIFFE identities** if running in containerized environment

### Network Segmentation
```
Internet → API Gateway (WAF, Rate Limit) 
         ↓
     Private Subnet
         ↓
    [Memory Engine] ← [Only from API Gateway]
    [FAISS Index]
    [HNSW Graph]
```

---

## 2. Authentication & Authorization

### Token Strategy
- **JWT tokens**: 15-minute max lifetime with refresh tokens
- **Validate every token claim**:
  ```python
  required_claims = {
      'iss': 'expected_issuer',
      'aud': 'memory-engine-api',
      'exp': current_time,
      'nbf': current_time,
      'sub': user_id
  }
  # REJECT if alg == "none"
  ```

### Service Identity
For edge deployments (Ryzen AI), use local attestation:
- **Hardware-bound credentials**: TPM 2.0 keys if available
- **Fallback**: Local encrypted keystore with file permissions `600`
- **Never** share secrets across service boundaries

### RBAC Model
```
Role: QUERY_ONLY
  - memory_engine:read_index
  - memory_engine:retrieve_embeddings
  
Role: ADMIN
  - memory_engine:write_index
  - memory_engine:reindex
  - memory_engine:delete_vectors
  - memory_engine:config_update
```

---

## 3. Traffic Management

### Rate Limiting (Apply at Gateway)
```python
# Per-IP / Per-API-Key
RATE_LIMITS = {
    "retrieve_relevant": {"calls": 100, "window_sec": 60},
    "ingest_vectors": {"calls": 10, "window_sec": 60},
    "reindex": {"calls": 1, "window_sec": 3600},
}
```

### Payload Size Limits
- **Vector ingestion**: Max 5MB per request (or per your FAISS config)
- **Query payloads**: Max 1MB
- **Reject oversize**: Return `413 Payload Too Large`

### Adaptive Throttling
- Monitor for abuse patterns (repeated 401/403)
- Implement exponential backoff for suspicious clients
- Log and alert on anomalies

---

## 4. Data Handling & Input Validation

### Vector Data Validation
```python
import numpy as np
from typing import List

def validate_vector_input(vectors: List[List[float]], expected_dim: int):
    """Validate embeddings before FAISS ingestion"""
    if not isinstance(vectors, list) or len(vectors) == 0:
        raise ValueError("vectors must be non-empty list")
    
    for i, vec in enumerate(vectors):
        if len(vec) != expected_dim:
            raise ValueError(f"Vector {i}: dimension mismatch")
        if not all(isinstance(x, (int, float)) for x in vec):
            raise ValueError(f"Vector {i}: non-numeric values")
        if any(np.isnan(x) or np.isinf(x) for x in vec):
            raise ValueError(f"Vector {i}: NaN or Inf detected")
    
    return np.array(vectors, dtype=np.float32)
```

### Query Sanitization
```python
def sanitize_query(query_str: str, max_length: int = 10000) -> str:
    """Prevent prompt injection and oversized queries"""
    if len(query_str) > max_length:
        raise ValueError(f"Query exceeds {max_length} chars")
    
    # Remove null bytes and control characters
    query_str = ''.join(c for c in query_str if ord(c) >= 32)
    
    return query_str.strip()
```

### Metadata Validation
```python
import json
from pydantic import BaseModel, validator

class VectorMetadata(BaseModel):
    id: str
    source: str
    timestamp: int
    user_id: str
    
    @validator('id')
    def validate_id(cls, v):
        # Prevent injection via IDs
        if len(v) > 256 or not v.isalnum():
            raise ValueError("Invalid ID format")
        return v
    
    @validator('user_id')
    def validate_user(cls, v):
        # Ensure user_id is sanitized
        if not v.isalnum():
            raise ValueError("Invalid user_id")
        return v
```

### Error Handling
```python
# ❌ BAD: Returns internal details
@app.post("/retrieve")
def retrieve(query: str):
    try:
        results = faiss_engine.search(query)
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

# ✅ GOOD: Generic error + logging
@app.post("/retrieve")
def retrieve(query: str):
    try:
        results = faiss_engine.search(query)
    except Exception as e:
        logger.error(f"Retrieve failed: {e}", exc_info=True, 
                     extra={"user_id": request.user_id})
        return {"error": "Internal error"}, 500
```

---

## 5. Security Headers & Configuration

### HTTP Security Headers
```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

### CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware

# ❌ WRONG
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# ✅ RIGHT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trusted-app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Correlation-ID"],
    max_age=600,
)
```

### Server Fingerprint Removal
```python
# Remove default framework headers
app.add_middleware(
    BaseHTTPMiddleware,
    dispatch=lambda request, call_next: (
        lambda response: (
            response.headers.pop("Server", None),
            response.headers.pop("X-Powered-By", None),
            response
        )[2]
    )(await call_next(request))
)
```

---

## 6. Secrets Management

### Local Edge Deployment (Ryzen AI 5 340)
```python
import os
from pathlib import Path
import json

class EdgeSecretsManager:
    """Secure secrets for edge deployment without cloud KMS"""
    
    SECRETS_DIR = Path("/opt/epiphany/secrets")  # Restricted: 700
    
    def __init__(self):
        self.SECRETS_DIR.mkdir(mode=0o700, exist_ok=True)
    
    def load_api_key(self, service_name: str) -> str:
        """Load encrypted service credentials"""
        key_path = self.SECRETS_DIR / f"{service_name}.key"
        if not key_path.exists():
            raise FileNotFoundError(f"Secret not found: {service_name}")
        
        # Verify file permissions (must be 600)
        stat = key_path.stat()
        if stat.st_mode & 0o077:
            raise PermissionError(f"Secret file has insecure permissions: {oct(stat.st_mode)}")
        
        with open(key_path, 'r') as f:
            return f.read().strip()
    
    @staticmethod
    def validate_env_vars():
        """Ensure sensitive vars are NOT in environment"""
        forbidden = ['API_KEY', 'TOKEN', 'PASSWORD', 'SECRET']
        for var in forbidden:
            if var in os.environ:
                raise RuntimeError(f"SECURITY: {var} found in environment variables")
```

### .env Configuration
```bash
# ❌ WRONG (never commit this)
# API_KEY=sk-1234567890abcdef
# DB_PASSWORD=mypassword123

# ✅ RIGHT (.env.example - no secrets)
# API_KEY_PATH=/opt/epiphany/secrets/api_key
# FAISS_INDEX_PATH=/var/lib/epiphany/indices
# LOG_LEVEL=INFO
```

### .gitignore
```
# Secrets
.env
.env.local
.env*.local
secrets/
*.key
*.pem
*.crt

# Credentials
aws_credentials
gcp_credentials.json
azure_credentials.json

# Sensitive data
faiss_indices/backup/
*.db
*.sqlite
*.log
```

---

## 7. Logging & Monitoring

### Structured Logging with Correlation IDs
```python
import logging
import uuid
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')

class CorrelationIDFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = correlation_id_var.get()
        return True

# Setup
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(correlation_id)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
handler.addFilter(CorrelationIDFilter())

@app.post("/retrieve")
async def retrieve(query: str):
    correlation_id = str(uuid.uuid4())
    correlation_id_var.set(correlation_id)
    
    logger.info(f"Query received: {len(query)} chars")
    # Traces entire request with same ID
    return results
```

### What NOT to Log
```python
# ❌ DANGEROUS
logger.info(f"User {user_id} submitted query: {query}")
logger.info(f"API Key: {api_key}")
logger.info(f"Response: {full_response_with_pii}")

# ✅ SAFE
logger.info(f"Query processed for user_id={user_id[:8]}...")
logger.info(f"Auth token accepted (first 10 chars: {token[:10]}...)")
logger.info(f"Response fields: {list(response.keys())}")
```

### Security Event Monitoring
```python
# Monitor for attacks
SECURITY_ALERTS = {
    "repeated_401": ("Failed auth 5+ times in 60s", "WARN"),
    "large_payload": ("Payload >5MB rejected", "WARN"),
    "invalid_vector_dim": ("Dimension mismatch attempt", "ALERT"),
    "reindex_attempt_unauthorized": ("Reindex without ADMIN role", "CRITICAL"),
    "suspicious_queries": ("Same query 100+ times in 60s", "WARN"),
}

def emit_security_alert(alert_type: str, context: dict):
    logger.warning(f"SECURITY_ALERT [{alert_type}] {context}")
    # Send to monitoring system (Datadog, New Relic, etc.)
```

---

## 8. Index & Data Protection

### FAISS Index Hardening
```python
import faiss
from pathlib import Path
import hashlib

class SecureIndexManager:
    def __init__(self, index_path: str):
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(mode=0o700, exist_ok=True)
        self.checksum_file = self.index_path.with_suffix('.sha256')
    
    def save_index(self, index: faiss.Index):
        """Save with integrity verification"""
        faiss.write_index(index, str(self.index_path))
        
        # Compute checksum
        with open(self.index_path, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        with open(self.checksum_file, 'w') as f:
            f.write(checksum)
        
        # Restrict permissions
        self.index_path.chmod(0o600)
        self.checksum_file.chmod(0o600)
        
        logger.info(f"Index saved with checksum: {checksum[:16]}...")
    
    def load_index(self) -> faiss.Index:
        """Load with integrity check"""
        with open(self.checksum_file, 'r') as f:
            expected_checksum = f.read().strip()
        
        with open(self.index_path, 'rb') as f:
            actual_checksum = hashlib.sha256(f.read()).hexdigest()
        
        if expected_checksum != actual_checksum:
            raise RuntimeError("Index integrity check failed - possible corruption/tampering")
        
        return faiss.read_index(str(self.index_path))
```

### Backup Security
```bash
#!/bin/bash
# Backup with encryption (use gpg, age, or kms)

BACKUP_DIR="/backup/epiphany-indices"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ✅ Encrypted backup
tar czf - /opt/epiphany/indices/ | \
  gpg --encrypt --recipient your-key-id > \
  "$BACKUP_DIR/indices_$TIMESTAMP.tar.gz.gpg"

# Set permissions
chmod 600 "$BACKUP_DIR/indices_$TIMESTAMP.tar.gz.gpg"

# Verify backup integrity
gpg --verify "$BACKUP_DIR/indices_$TIMESTAMP.tar.gz.gpg"
```

---

## 9. Deployment Checklist

- [ ] **TLS 1.3 enabled**, weak ciphers disabled
- [ ] **Secrets manager configured**, no .env in repo
- [ ] **CORS explicitly limited**, no wildcards
- [ ] **Rate limiting deployed** at gateway
- [ ] **Input validation** on all endpoints (vectors, queries, metadata)
- [ ] **Error handling** returns generic messages, details logged only
- [ ] **Logging configured** with correlation IDs, PII masked
- [ ] **FAISS index** protected (file perms 600, checksum verified)
- [ ] **Security headers** set (HSTS, CSP, X-Frame-Options, etc.)
- [ ] **mTLS** between services enabled
- [ ] **Dependency audit** run (`pip audit` for Python deps)
- [ ] **File permissions** verified on secrets (600), config (644)

---

## 10. Incident Response

### If Compromise Suspected
1. **Isolate** memory engine from network immediately
2. **Rotate** all API keys and tokens
3. **Audit** access logs (correlation IDs to trace attacker path)
4. **Verify** FAISS index integrity (checksums)
5. **Review** what queries/data were accessed
6. **Rebuild** index from verified backup
7. **Deploy** patched version with updated secrets

### Contact & Escalation
- **Security contact**: [YOUR-EMAIL]
- **Incident severity**: CRITICAL → immediate isolation, INFO → log and monitor
- **Post-mortem**: Review within 48 hours of incident

---

## References
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [FAISS Security Best Practices](https://faiss.ai/index.html)
- [TLS 1.3 RFC 8446](https://tools.ietf.org/html/rfc8446)
