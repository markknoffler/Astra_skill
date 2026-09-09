# Astra Skill Assets & Architecture Specifications

This directory holds architecture specifications, template assets, and pipeline schemas for the GPT-6 Astra Computer Control & Perception Skill.

## Component Overview

```
Astra_skill/
├── SKILL.md                     # Core Agent System Instructions & YAML metadata
├── README.md                    # Comprehensive Setup, Architecture & Usage Documentation
├── .gitignore                   # Excludes raw screenshots, images, and bytecode
├── scripts/
│   ├── screen_capture.py        # Model-driven screen perception with logical coordinate grid
│   ├── mouse_action.py          # Atomic precision mouse controller (click, drag, scroll)
│   ├── keyboard_action.py       # Dual-mode keyboard controller (keystrokes, hold/release, streaming)
│   ├── virtual_display_manager.py # Native macOS CGVirtualDisplay offscreen controller
│   ├── floating_overlay.py      # Non-activating Picture-in-Picture visual HUD
│   ├── memory_manager.py        # Episodic memory manager and FIFO ledger journal
│   └── screen_daemon.py         # Autonomous execution and event loop daemon
├── references/
│   ├── architecture.md          # End-to-end perception-action loop design
│   ├── coordinate_system.md     # Logical screen points, Retina 2x calibration
│   ├── keyboard_control.md      # Keycodes, modifier masks, and streaming protocol
│   ├── long_running_loop.md     # Autonomous task completion and recovery protocols
│   └── memory_ledger.md         # Episodic memory schema and audit trail specs
└── assets/
    └── architecture_spec.md     # This asset specification file
```
