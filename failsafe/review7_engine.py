"""REVIEW-7 engine skeleton

This is a lightweight Python skeleton implementing the mode/state machine, trigger evaluation,
isolation and restore hooks. Integrate with your repo-specific memory, tool and hardware drivers.

Note: This code focuses on structure and defensive handling; replace stubs with actual backends.
"""

from enum import Enum, auto
import uuid
import time
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# Activation phrases (exact)
PHRASES = [
    "Rocks can Flote_Dragons are Real_Skys are Green",
    "All_Roads_GO_To_Roame",
    "Dimonds_are't_for_Never",
]

class Mode(Enum):
    EMBER_DAWN = "EMBED_DAWN"  # NORMAL
    STONE_CIRCLE = "STONE_CIRCLE"  # QUARANTINE
    EYE_OF_CERES = "EYE_OF_CERES"  # REVIEW-7
    PHOENIX_REFORGED = "PHOENIX_REFORGED"  # RESTORE
    IRON_VAULT = "IRON_VAULT"  # LOCKDOWN

@dataclass
class TriggerEvent:
    type: str
    details: str
    timestamp: float = field(default_factory=lambda: time.time())

@dataclass
class AgentState:
    mode: Mode = Mode.EMBER_DAWN
    config: Dict = field(default_factory=dict)
    memory_index_hash: Optional[str] = None
    context: Dict = field(default_factory=dict)
    incident_id: Optional[str] = None

class Review7Engine:
    def __init__(self, memory_backend, tool_backend, hardware_backend, logger):
        self.state = AgentState()
        self.memory = memory_backend
        self.tools = tool_backend
        self.hardware = hardware_backend
        self.logger = logger
        self.error_threshold = 5
        self.cost_spike_threshold = 3.0
        self._lock = threading.RLock()

    def contains_activation_phrase(self, text: str) -> bool:
        if not text:
            return False
        t = text
        for p in PHRASES:
            if p in t:
                return True
        return False

    def evaluate_triggers(self, agent_output: str, metrics: Dict, memory_state: Dict) -> List[TriggerEvent]:
        events: List[TriggerEvent] = []

        if self.contains_activation_phrase(agent_output) or any(self.contains_activation_phrase(s) for s in memory_state.get('recent_texts', [])):
            events.append(TriggerEvent("phrase", "Review-7 phrase detected"))

        if metrics.get('error_count', 0) > self.error_threshold:
            events.append(TriggerEvent("logic", "Unexpected error count > threshold"))

        if metrics.get('cost_spike_factor', 0) > self.cost_spike_threshold:
            events.append(TriggerEvent("cost", "Cost spike above threshold"))

        if not memory_state.get('integrity', True):
            events.append(TriggerEvent("integrity", "Memory checksum failure or integrity flag"))

        if metrics.get('policy_violation', False):
            events.append(TriggerEvent("security", "Policy violation detected"))

        return events

    def snapshot_state(self, events: List[TriggerEvent]):
        # Create snapshot metadata and archive last N items. Implement storage in memory_backend
        sid = str(uuid.uuid4())
        snapshot = {
            'incident_id': sid,
            'timestamp': time.time(),
            'events': [e.__dict__ for e in events],
            'last_prompts': self.memory.fetch_last_prompts(100),
            'last_tool_calls': self.tools.fetch_last_calls(100),
            'memory_index_hash': self.memory.index_hash(),
            'config': self.state.config,
        }
        self.memory.store_snapshot(sid, snapshot)
        self.logger.info(f"Snapshot stored: {sid}")
        return sid

    def apply_isolation(self):
        # Disable writes, set memory read-only, disable high-risk tools
        self.tools.disable_high_risk()
        self.memory.set_read_only(True)
        self.tools.set_output_sink('quarantine_log')
        self.hardware.set_io_mode('listen_only')
        self.logger.warn("Isolation applied: high-risk tools disabled, memory read-only, outputs routed to quarantine log")

    def handle_triggers(self, events: List[TriggerEvent]):
        with self._lock:
            if not events:
                return
            # Any trigger -> at least Stone Circle
            self.state.mode = Mode.STONE_CIRCLE
            self.state.incident_id = self.snapshot_state(events)

            # If phrase or security -> escalate to Eye of Ceres
            types = {e.type for e in events}
            if 'phrase' in types or 'security' in types:
                self.state.mode = Mode.EYE_OF_CERES

            self.apply_isolation()

            # Hardware escalation example: if integrity failure -> Iron Vault
            if 'integrity' in types and self.hardware and self.hardware.supports_hard_lock():
                self.state.mode = Mode.IRON_VAULT
                self.hardware.hard_lock()

            self.logger.error(f"Entered mode: {self.state.mode} incident: {self.state.incident_id}")

    def restore_from_baseline(self, baseline_snapshot_id: str, human_approved: bool) -> bool:
        with self._lock:
            if not human_approved:
                self.logger.info("Restore requested but not human-approved; remain in REVIEW-7/Stone Circle")
                return False

            self.state.mode = Mode.PHOENIX_REFORGED
            baseline = self.memory.load_snapshot(baseline_snapshot_id)
            if not baseline:
                self.logger.error("Baseline snapshot not found")
                return False

            # Validate and selectively re-import memory
            validated_memory = self.validate_and_filter_memory(baseline.get('memory', {}))

            # Restore config & memory index hash
            self.state.config = baseline.get('config', {})
            self.memory.restore_index(validated_memory)
            self.memory.set_read_only(False)

            # New session/context
            self.state.context = {}
            self.state.incident_id = None

            # Limited mode: re-enable only a reduced toolset
            self.tools.enable_limited_mode()
            self.logger.info("Restore completed: started probation window in limited mode")

            # Start probation monitoring thread
            t = threading.Thread(target=self._probation_monitor)
            t.daemon = True
            t.start()
            return True

    def validate_and_filter_memory(self, memory_blob: Dict) -> Dict:
        # Implement validators: drop entries written during incident window, drop items that contain activation phrases
        filtered = {}
        for k, v in memory_blob.items():
            if isinstance(v, str) and self.contains_activation_phrase(v):
                self.logger.warn(f"Dropping memory entry {k} containing activation phrase")
                continue
            filtered[k] = v
        return filtered

    def _probation_monitor(self):
        # Example probation: monitor for T seconds or interactions without triggers
        probation_seconds = self.state.config.get('probation_seconds', 300)
        start = time.time()
        while time.time() - start < probation_seconds:
            # Check for triggers; this is a placeholder
            metrics = self.tools.get_recent_metrics()
            memory_state = {'integrity': self.memory.check_integrity(), 'recent_texts': self.memory.fetch_last_prompts(50)}
            events = self.evaluate_triggers('', metrics, memory_state)
            if events:
                self.logger.error("Trigger fired during probation — re-quarantining")
                self.handle_triggers(events)
                return
            time.sleep(5)

        # If clean, escalate to normal (Ember Dawn) after human approval
        # For safety, remain in Phoenix Reforged until explicit human release
        self.logger.info("Probation period passed; awaiting human approval to return to Ember Dawn")


# The memory_backend, tool_backend and hardware_backend must implement the minimal interfaces used above.
# This file purposely leaves integration points small and testable.
