# REVIEW-7 (Reveiw-7) — Agent Preservation Protocol

Code name: REVIEW-7 (user variant: "Reveiw-7")
Target: Dragon-Wing AI Totem (AI hub device)

Purpose
- Fail-safe system for agentic AI with tools, memory, and long-running tasks.
- Detect corruption and drift, isolate reasoning core, snapshot state, restore from trusted baseline, and require human review before re-enabling high-risk capabilities.

Contents in this folder:
- REVIEW-7_SPEC.md — full specification and Totem mythic labels / LED & hologram language
- review7_engine.py — Python skeleton implementing the state machine, trigger detection, isolation, snapshot and restore hooks (pluggable backends: memory, tools, hardware)
- hardware_dragon_wing.md — hardware-level protocol for the Dragon-Wing Totem (safety MCU, bus gating, protected golden image)

Notes
- This is a starting implementation skeleton and spec. Integrate with your repository's memory engine and hardware API drivers.
