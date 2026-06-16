# Dragon-Wing Totem — Hardware Protocol (summary)

This document captures the hardware-level requirements and sequences for the Dragon-Wing Totem safety behavior.

Safety rings
- Core Compute Ring: AI accelerator, CPU, RAM. Runs the reasoning core.
- Perimeter I/O Ring: radios, sensors, actuators, external ports.
- Safety Control Ring: independent MCU (safety MCU) that can gate power, buses, and re-flash the core.

Hardware capabilities required
- Safety MCU with tamper-resistant secure storage (to hold golden image hashes and unlock secrets)
- GPIO/button for human unlock with secure code entry (multi-factor: physical + code)
- Bus gating hardware or transceivers that can be set to listen-only
- Watchdog mechanism to forcibly reset core and preserve safety MCU state
- Protected ROM for golden firmware image or secure external flash with hardware lock

Lock / isolation sequence (when controller requests quarantine or MCU detects policy violation):
1. Safety MCU asserts bus isolation and sets I/O ring to listen-only
2. Safety MCU sets flash/NVRAM regions to read-only (firmware flag or protection bit)
3. Disable motor/actuator drivers and high-power outputs
4. Notify core that it's in QUARANTINE; if the core continues forbidden actions, watchdog resets the core

Restore sequence (human unlock):
1. Operator provides physical press + secure code to Safety MCU
2. MCU performs integrity checks and may re-flash core from golden image
3. MCU selectively unlocks validated memory regions (via protection flags)
4. I/O remains gated until the core passes self-tests and probation checks

Physical indicators
- LED ring and hologram projector must be driven by the safety MCU to ensure consistent meaning even if core is compromised.
- LED/hologram language mapping is in REVIEW-7_SPEC.md

Integration notes
- Provide a secured console (over a dedicated management channel) for human review that fetches the quarantine snapshot and incident report; this path must be separate from general network interfaces.
- Keep golden images and snapshot hashes in tamper-resistant storage on the safety MCU.
