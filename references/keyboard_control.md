# Precision Keyboard Control & High-Speed Streamer Architecture

## Overview
Complex GUI applications (such as **Blender**, **Unreal Engine**, **NVIDIA Isaac Sim**, CAD tools, and IDEs) rely heavily on precise keyboard interactions. The Astra agent provides a dual-mode keyboard subsystem designed to handle any desktop application:

```
+-------------------------------------------------------------------------+
|                        GPT-6 Astra Keyboard Suite                       |
+-------------------------------------------------------------------------+
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
+------------------------------------+   +------------------------------------+
| MODE 1: Targeted Real-Time Strokes |   | MODE 2: File-to-Cursor Streamer    |
| - Discrete strokes (G, S, R, Tab)  |   | - Agent writes code in CWD         |
| - Key combinations (Shift+A, Alt+P)|   | - Focuses cursor at target UI area |
| - Key hold & release (Shift, W)    |   | - Rapid burst stream / Cmd+V paste |
| - Continuous 3D/Sim viewport drive |   | - Ingests 500+ lines in ~0.05s     |
+------------------------------------+   +------------------------------------+
```

---

## Mode 1: Targeted Real-Time Input Strokes & Hold States

### 1. Application-Specific Interactive Controls
Modern 3D and simulation software rely on modal hotkeys and hold-states:

- **Blender**:
  - `Shift + A`: Open Add Object / Node menu.
  - `G` / `S` / `R`: Grab/Translate, Scale, Rotate modal operations.
  - `X` or `Delete`: Delete active selection.
  - `Alt + P`: Execute active Python script in Text Editor.
  - `Shift + F11`: Switch active panel to Text Editor.
  - `Shift + F4`: Switch active panel to Python Interactive Console.
  - `Shift + F5`: Switch active panel to 3D Viewport.
  - `Numpad 1 / 3 / 7`: Front / Right / Top orthographic views.
  - `Tab`: Toggle Edit Mode and Object Mode.

- **Unreal Engine & NVIDIA Isaac Sim**:
  - `Hold Right-Click + W / A / S / D`: Fly-through viewport camera navigation.
  - `F`: Focus / Frame selected actor in viewport.
  - `W` / `E` / `R`: Translate, Rotate, Scale gizmo toggles.
  - `Ctrl + Space`: Open Content Drawer.
  - `Ctrl + Shift + S`: Save All assets and levels.

### 2. Command Reference for Mode 1
```bash
# Execute discrete keystroke sequence (e.g. confirm deletion with Enter)
python3 <skill_dir>/scripts/keyboard_action.py stroke --keys x enter --interval 0.1

# Trigger hotkey combinations
python3 <skill_dir>/scripts/keyboard_action.py hotkey --keys shift a
python3 <skill_dir>/scripts/keyboard_action.py hotkey --keys alt p
python3 <skill_dir>/scripts/keyboard_action.py hotkey --keys command s

# Hold key down for duration (e.g. hold Shift while panning or W to move forward)
python3 <skill_dir>/scripts/keyboard_action.py hold --key shift --duration 1.5

# Stateful Hold & Release (for coordinated mouse + keyboard actions)
python3 <skill_dir>/scripts/keyboard_action.py down --key shift
python3 <skill_dir>/scripts/mouse_action.py drag --start-x 400 --start-y 400 --end-x 600 --end-y 400
python3 <skill_dir>/scripts/keyboard_action.py up --key shift
```

---

## Mode 2: Bulk File-to-Cursor Fast Streamer (`stream_file`)

### The Code Ingestion Challenge
When the AI agent needs to write a sophisticated 3D model generator, simulation harness, or large data script (100–1000+ lines), manually typing character-by-character is slow and risks dropping characters or breaking indentation.

### The Astra Pipeline Solution:
1. **Model Generates Code Locally in CWD**:
   The agent creates the Python script in its current working directory (e.g. `cwd/train_model.py`).
2. **Focus Target Text Area**:
   The agent clicks the target text area, editor, or console using `mouse_action.py click --x <X> --y <Y>`.
3. **Execute High-Speed File Stream**:
   The agent calls `stream_file`:
   ```bash
   python3 <skill_dir>/scripts/keyboard_action.py stream_file --file train_model.py --method paste
   ```
4. **Immediate Execution**:
   The agent triggers the run hotkey (e.g. `alt p` in Blender, or `enter` in console) to execute the complete script.
5. **Continuous Verification**:
   The agent captures a screenshot (`screen_capture.py`) immediately to monitor the generated 3D mesh or simulation state.
