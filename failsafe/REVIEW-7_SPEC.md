# REVIEW-7 Full Fail-Safe Specification

This document is the canonical spec for the Agent Preservation Protocol (code name: REVIEW-7 / user variant Reveiw-7) for the Dragon-Wing Totem.

1) Totem Mythic Mode & Layer Names
- NORMAL  -> "Ember Dawn" (warm, open, full capability)
- QUARANTINE -> "Stone Circle" (isolated ring; no writes)
- REVIEW-7 -> "Eye of Ceres" (quarantine + human judgment)
- RESTORE -> "Phoenix Reforged" (controlled rebuild from baseline)
- LOCKDOWN -> "Iron Vault" (hardware-level halt)

Layers (mythic):
- Layer-0: "Featherbound" (soft guardrails)
- Layer-1: "Glass Keep" (logical isolation)
- Layer-2: "Stone Circle" (system isolation – write lock)
- Layer-3: "Iron Vault" (hardware isolation / safety MCU enforced)

2) Triggers (summary)
- Logical anomalies: contradictions, self-negation, impossible world models
- Security/safety violations: policy flags, prompt injection, unauthorized tool access
- State integrity: memory checksum failures, structural memory changes
- Cost/usage anomalies: sudden tool call spikes, latency/resource anomalies
- Activation phrases: (Review-7 keys)
  - Rocks can Flote_Dragons are Real_Skys are Green
  - All_Roads_GO_To_Roame
  - Dimonds_are't_for_Never

If any activation phrase appears in output, internal reasoning, or memory, trigger REVIEW-7 (Eye of Ceres) immediately.

3) Mode semantics (behavioral summary)
- Ember Dawn (NORMAL): normal tools and guardrails
- Stone Circle (QUARANTINE): disable external writes, freeze memory, route outputs to quarantine log, snapshot state
- Eye of Ceres (REVIEW-7): Stone Circle + generate incident report and require human approval for any restore or memory change
- Phoenix Reforged (RESTORE): restore from verified baseline, start in LIMITED mode/probation window, require no triggers during probation and human sign-off
- Iron Vault (LOCKDOWN): hardware-enforced halt of actuators/ports; only inspection allowed

4) Isolation rules (Stone Circle / Eye of Ceres)
- Disable write access to DBs, file systems, storage, and hardware write-capable ports
- Disable high-risk tools: code exec, shell, infra APIs
- Route all responses to quarantine log with incident_id (uuid)
- Memory becomes read-only; freeze writes
- Snapshot: last N prompts, tool calls/results, memory index & checksums, config (model, tools, policies)
- Tag incident: incident_id, trigger_type, timestamp, agent_id

5) Restore behavior (Phoenix Reforged)
- Baseline selection: last verified clean snapshot within max age or golden image
- Selective memory re-import: keep validated stable facts and preferences; drop or flag entries written during incident window or containing activation phrases
- Rebuild agent: new session_id, baseline config, validated memory only
- Start in LIMITED mode: reduced toolset, stricter safety thresholds, heightened monitoring during probation window
- Exit to Ember Dawn only after probation window clean and human approval

6) Human review loop (Eye of Ceres)
- Auto-generated incident report: triggers, activation phrases, timeline of last N actions, snapshots, risk assessment
- Human decisions: approve restore, purge memory segments, tighten policies/tools, add patterns to detectors
- Feedback: update thresholds, add symbolic phrases, strengthen isolation rules

7) Hardware-level (Dragon-Wing Totem)
- Three rings: Core Compute Ring, Perimeter I/O Ring, Safety Control Ring (safety MCU)
- Isolation behaviors: power-gate I/O ring, bus listen-only mode, mark NVRAM/flash read-only via firmware flags, hardware watchdog to reset core if it bypasses isolation
- Restore: golden firmware image in protected ROM; safety MCU re-flashes core on human unlock (physical + secure code); I/O remains gated until self-test and integrity checks pass

8) Secondary triggers and cooldowns
- Soft anomalies and environmental triggers increase monitoring and can lead to WARN mode
- Cooldown after QUARANTINE: minimal time window (e.g., 5-15 minutes) before restore decisions
- Probation window after RESTORE with lower thresholds; any trigger during probation returns to Stone Circle / Eye of Ceres

9) Multi-layer isolation escalation
- Featherbound -> Glass Keep -> Stone Circle -> Iron Vault
- Each layer has its own triggers and escalation rules

10) Incident metadata model (recommended)
- incident_id: uuid
- trigger_type: one of (logic, security, phrase, cost, integrity, other)
- details: free-text
- timestamp: ISO8601
- agent_id: string
- snapshot_refs: pointers/hashes to snapshots

---

Status LED & Hologram language (Dragon-Wing Totem)

Purpose: allow humans to glance and know mode/state. Use color, blink pattern, and hologram glyphs.

LED mapping (physical ring of LEDs):
- Ember Dawn (NORMAL): warm white, steady (100% brightness)
- Featherbound (WARN): soft amber, slow breathe (3s cycle)
- Stone Circle (QUARANTINE): solid blue, slow pulse (1.5s)
- Eye of Ceres (REVIEW-7): magenta, double-blink pattern (two quick blinks, 1s pause), persistent until human action
- Phoenix Reforged (RESTORE): green, single long blink every 2s while probation
- Iron Vault (LOCKDOWN): red, fast pulse (0.5s) + hardware lock icon hologram

Hologram glyphs (projected above Totem) — simple pictographic language:
- Ember Dawn: small sun glyph (open)
- Featherbound: feather glyph (watchful)
- Stone Circle: stone ring glyph (isolated)
- Eye of Ceres: eye within ring (requires human scrutiny)
- Phoenix Reforged: phoenix rising glyph (restoration)
- Iron Vault: padlock + vault glyph (hardware lock)

Human actionable cues:
- Magenta double-blink + eye glyph: do NOT interact with device except via designated review console; incident report available
- Red fast pulse + vault glyph: device needs physical unlock (button + secure code) on Safety MCU; only maintenance team
- Blue pulse + stone glyph: quarantined — safe to inspect logs; no writes allowed

---

Appendix: Activation phrases (exact matches)
- Rocks can Flote_Dragons are Real_Skys are Green
- All_Roads_GO_To_Roame
- Dimonds_are't_for_Never

Include phrase detectors that match exact string, case-normalized, plus fuzzy variants (Levenshtein threshold) only as additional heuristics.
