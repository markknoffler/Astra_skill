# GPT-6 Astra System Architecture

## Overview
GPT-6 Astra is an autonomous, continuous multimodal computer-use agent architecture. It bridges high-level semantic reasoning with direct, low-level OS GUI interaction.

The system is composed of four decoupled, highly specialized modules:

```
+-------------------------------------------------------------------------+
|                         Autonomous OS Desktop                           |
+-------------------------------------------------------------------------+
                                    |
            [1] 2-Second Autonomous Screenshot (Quartz/OS)
                                    v
+-------------------------------------------------------------------------+
|                  Perception Daemon (screen_daemon.py)                   |
|  - Continuous non-intrusive 2.0s capture                                |
|  - Subtle semi-transparent coordinate grid overlay (logical points)     |
|  - 50-Frame FIFO Rolling Buffer (automatic disk cleanup)                |
|  - Atomic output to screenshots/latest.png & latest_clean.png           |
+-------------------------------------------------------------------------+
                                    |
             [2] Reads latest.png & visual inspection
                                    v
+-------------------------------------------------------------------------+
|                         AI Reasoning Engine                             |
|  - Compares visual screen state against user task goal                  |
|  - Extracts critical text, UI widgets, dialog messages                  |
|  - Consults episodic history in working-directory memory               |
|  - Identifies target coordinate (X, Y) via overlaid grid               |
+-------------------------------------------------------------------------+
            |                                               |
 [3] Updates Working Dir Memory                  [4] Atomic Screen Action
            v                                               v
+---------------------------------------+   +-----------------------------+
| Memory System (astra_memory.md in CWD)|   | Atomic Controllers          |
| - Screen-by-screen journal            |   | - mouse_action.py           |
| - Critical entity vault               |   |   (move, click, drag, zoom) |
| - Obstacle & navigation bug fixes     |   | - keyboard_action.py        |
+---------------------------------------+   |   (type, press, hotkey)     |
                                            +-----------------------------+
                                                            |
                                            [5] OS Input Event Injection
                                                            v
                                            +-----------------------------+
                                            |       Screen Updates        |
                                            +-----------------------------+
```

## Core Tenets

1. **Autonomous Perception Decoupling**: The AI model does not manually take screenshots; the background daemon continuously captures and renders the coordinate grid every 2 seconds.
2. **Atomic Execution**: Every command invocation performs exactly one deterministic action, returning structured JSON status. Complex workflows are composed sequentially or simultaneously.
3. **Episodic Durability**: Because screenshot storage strictly purges old frames after 50 captures to save disk space, the agent must treat `astra_memory.md` in its working directory as its permanent long-term memory.
4. **Self-Verifying Loop**: No action is assumed successful until the subsequent screenshot frame visually confirms state change.
