---
name: gpt-6-astra
description: Model-driven continuous screen perception and computer control skill inspired by GPT-6 Astra. The AI agent actively controls when to capture screenshots with a subtle non-intrusive coordinate grid, inspects screen state at each level, executes atomic mouse actions (move, click, right_click, double_click, drag, scroll, zoom), drives dual-mode precision keyboard interactions (targeted real-time strokes, key hold/release states for 3D/Sim engines like Blender/Unreal/Isaac Sim, and high-speed file-to-cursor code streamers), continuously verifies screen changes after every interaction, maintains persistent episodic memory in a working-directory Markdown log across 50-screenshot FIFO deletions, and persists until long-running tasks are completed.
---

# GPT-6 Astra: Model-Driven Screen Perception & Computer Control

This skill equips an AI agent with the continuous perception and precise GUI interaction loop inspired by **GPT-6 Astra**.

Unlike passive timers, the AI agent is the **active driver**:
- The agent decides **when** to capture screenshots and **when** to inspect the screen.
- At **each level and after every mouse or keyboard action**, the agent captures a fresh screenshot to continuously monitor the screen, verify state changes, and calibrate cursor movements.
- The agent executes **atomic actions** (one function at a time) via dedicated mouse and keyboard actuators.
- **Dual-Mode Keyboard Control**:
  1. *Targeted Real-Time Strokes & Holds*: Single strokes, key combinations, and hold/release states to manipulate complex interactive software (Blender, Unreal Engine, NVIDIA Isaac Sim, CAD, IDEs).
  2. *Bulk File-to-Cursor Fast Streamer*: Writes large scripts or code blocks into local files in CWD, focuses the target text field, and streams/pastes them into the cursor location in milliseconds.
- The agent maintains a persistent **`astra_memory.md`** journal in its **current working directory (CWD)**, preserving visual observations, coordinates, and bug fixes across 50-screenshot FIFO deletions.
- The agent runs continuously as a **long-running agent**, persevering through obstacles until the goal is fully accomplished.

---

## 1. The Autonomous Step-by-Step Loop

At every level of the task, follow this strict 5-step cycle:

```
+-------------------------------------------------------------------------+
|                  1. CAPTURE ON-DEMAND SCREENSHOT                        |
|  Run: python3 <skill_dir>/scripts/screen_capture.py                     |
|  -> Generates screenshots/latest.png with non-intrusive coordinate grid |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                    2. INSPECT & PARSE SCREEN STATE                      |
|  - Check URL / active window / focused element / modal dialogs          |
|  - Locate target element coordinates (X, Y) using grid chips & rulers   |
|  - Extract needed text, IDs, codes, or status messages                  |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|             3. UPDATE WORKING-DIRECTORY MEMORY (CWD)                    |
|  Log observations, extracted entities, and bug fixes into               |
|  `astra_memory.md` (mandatory because screenshots purge after 50 frames)|
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                  4. EXECUTE ATOMIC ACTION                               |
|  Option A: Mouse interaction                                            |
|    python3 <skill_dir>/scripts/mouse_action.py click --x <X> --y <Y>    |
|    python3 <skill_dir>/scripts/mouse_action.py scroll --dy -250         |
|  Option B: Targeted real-time keystrokes / hold states                  |
|    python3 <skill_dir>/scripts/keyboard_action.py hotkey --keys shift a |
|    python3 <skill_dir>/scripts/keyboard_action.py hold --key w --duration 1.0
|  Option C: Bulk code injection via file streamer                        |
|    Write script in CWD -> focus cursor -> stream_file --file <script>   |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|              5. CAPTURE & VERIFY TRANSITION AT NEXT LEVEL               |
|  Immediately run: python3 <skill_dir>/scripts/screen_capture.py         |
|  - Did the button press or script execution trigger the expected state?|
|  - Did a 3D mesh appear? Did the simulation update?                     |
|  - If unexpected or stuck: Apply corrective action & log fix in memory  |
|  - If goal accomplished: Conclude and report final results              |
|  - If task ongoing: Return to Step 2 for next level                     |
+-------------------------------------------------------------------------+
```

---

## 2. On-Demand Screen Capture Tool (`screen_capture.py`)

The AI model runs this tool whenever it needs to inspect the screen.

```bash
# Capture current screen with coordinate grid overlay
python3 <skill_dir>/scripts/screen_capture.py

# Optional: custom grid step (default: 100 logical points)
python3 <skill_dir>/scripts/screen_capture.py --grid-step 50

# Targeted App Window Capture (Background Quartz Buffer - Zero Focus Stealing)
python3 <skill_dir>/scripts/screen_capture.py --app Blender
```

### What It Produces:
- **`screenshots/latest.png`**: The newest screenshot with subtle, semi-transparent coordinate grid. Lines and chips are calibrated directly to **logical screen points** (0 to W, 0 to H).
- **`screenshots/latest_clean.png`**: Raw screen capture without grid (useful for reading small text or optical clarity).
- **`screenshots/history/frame_<timestamp>.png`**: Timestamped frame in the rolling history buffer.
- **50-Screenshot FIFO Rolling Buffer**: To conserve disk space, once 50 screenshots are stored, older frames are automatically purged.
- **`screenshots/metadata.json`**: JSON file containing resolution, scaling factor, and timestamps.

---

## 3. Background Multi-Tasking & Overlay Tools

### A. Non-Activating Picture-in-Picture Floating Overlay (`floating_overlay.py`)
Launches a translucent macOS floating HUD panel using `NSWindowStyleMaskNonactivatingPanel` and `NSFloatingWindowLevel`:
```bash
python3 <skill_dir>/scripts/floating_overlay.py --image screenshots/latest.png --width 420 --height 270
```
- Floats over all virtual desktops and Mission Control spaces.
- **Never steals keyboard or mouse focus** from the user's active window.
- Allows the user to monitor live agent perception while continuing their own work.

### B. Native macOS Virtual Display Controller (`virtual_display_manager.py`)
Creates and manages an isolated 1920x1080 60Hz virtual display using macOS native CoreGraphics Objective-C runtime (`CGVirtualDisplay`):
```bash
python3 <skill_dir>/scripts/virtual_display_manager.py
```
- Instantiates a second virtual monitor without third-party drivers.
- Moves target application windows (e.g., Blender) to the virtual display space via the macOS Accessibility API (`AXUIElementSetAttributeValue`).
- Enables full-resolution offscreen rendering while leaving the user's main screen 100% free.

---

## 3. Atomic Mouse Actuator (`mouse_action.py`)

Each invocation performs **exactly one atomic action**.

```bash
# Report current cursor position and screen dimensions
python3 <skill_dir>/scripts/mouse_action.py position

# Move mouse cursor to (x, y)
python3 <skill_dir>/scripts/mouse_action.py move --x 500 --y 300

# Left click at (x, y)
python3 <skill_dir>/scripts/mouse_action.py click --x 500 --y 300

# Right click (context menu) at (x, y)
python3 <skill_dir>/scripts/mouse_action.py right_click --x 500 --y 300

# Double click at (x, y)
python3 <skill_dir>/scripts/mouse_action.py double_click --x 500 --y 300

# Drag and drop from start to end
python3 <skill_dir>/scripts/mouse_action.py drag --start-x 200 --start-y 200 --end-x 600 --end-y 400

# Scroll page (positive dy = scroll up, negative dy = scroll down)
python3 <skill_dir>/scripts/mouse_action.py scroll --dy -300

# Zoom in or out (positive = zoom in, negative = zoom out)
python3 <skill_dir>/scripts/mouse_action.py zoom --amount 5 --x 600 --y 400

# Hover at (x, y)
python3 <skill_dir>/scripts/mouse_action.py hover --x 400 --y 200 --duration 1.0
```

---

## 4. Dual-Mode Precision Keyboard Controller (`keyboard_action.py`)

### Mode 1: Targeted Real-Time Strokes & Hold Controls
Ideal for real-time control in **Blender**, **Unreal Engine**, **NVIDIA Isaac Sim**, and interactive viewports.

```bash
# Execute discrete keystroke sequence
python3 <skill_dir>/scripts/keyboard_action.py stroke --keys x enter --interval 0.1

# Trigger hotkey combinations
python3 <skill_dir>/scripts/keyboard_action.py hotkey --keys shift a       # Blender: Add Menu
python3 <skill_dir>/scripts/keyboard_action.py hotkey --keys alt p          # Blender: Run Script
python3 <skill_dir>/scripts/keyboard_action.py hotkey --keys command s      # Save file

# Hold a key down for duration (e.g. holding navigation keys in 3D/Sim engines)
python3 <skill_dir>/scripts/keyboard_action.py hold --key shift --duration 2.0
python3 <skill_dir>/scripts/keyboard_action.py hold --key w --duration 1.0

# Stateful Hold and Release (for complex coordinated mouse+keyboard actions)
python3 <skill_dir>/scripts/keyboard_action.py down --key shift
python3 <skill_dir>/scripts/mouse_action.py click --x 500 --y 500
python3 <skill_dir>/scripts/keyboard_action.py up --key shift
```

### Mode 2: Bulk File-to-Cursor Fast Streamer (`stream_file`)
When the model needs to input large blocks of code, scripts, or multiline text:
1. Write the script or content into a file in your **current working directory (CWD)** (e.g. `train_generator.py`).
2. Focus the target text box or editor in the application using `mouse_action.py click --x <X> --y <Y>`.
3. Call `stream_file`:
```bash
# Ingest entire file into focused cursor position instantly via paste
python3 <skill_dir>/scripts/keyboard_action.py stream_file --file train_generator.py --method paste

# Alternative: line-by-line keystroke streaming
python3 <skill_dir>/scripts/keyboard_action.py stream_file --file script.py --method keystroke --line-delay 0.02
```

---

## 5. Working-Directory Memory Ledger (`astra_memory.md`)

### The Storage Rule
> **CRITICAL**: The episodic task memory file `astra_memory.md` MUST live in the **current working directory (CWD)** where the agent is running, NOT in the skills directory.

### Why It Is Essential
Because `screen_capture.py` deletes older screenshots once 50 frames are collected, past visual frames are permanently lost after 50 captures. The markdown file is the agent's **durable episodic memory**.

### Memory Ledger Template:
```markdown
# GPT-6 Astra Task Memory & Screen Journal

**Initialized:** [Timestamp]  
**Working Directory:** [CWD Path]  
**Primary Goal:** [User Task Goal]

---

## Task Overview & Progress State
- **Status:** In Progress
- **Current Subgoal:** [e.g., Run train generator script in Blender]
- **Screens Perceived:** [Count]
- **Actions Executed:** [Count]

---

## Critical Extracted Information & Entity Vault
> Data, codes, order IDs, account names, and URLs seen on screen that may be needed later.
- **Blender Version:** `Blender 5.1.1`
- **Active Workspace:** `Scripting`

---

## Navigation Obstacles, UI Quirks & Resolution Log
> Record of problems, misclicks, unresponsive buttons, and how they were solved.
- **Obstacle at Workspace Switch:** Click at `(705, 78)` selected Animation tab because Scripting is located at `X:1045`.
  - **Resolution:** Targeted `X:1045, Y:78` to enter Scripting workspace.

---

## Chronological Screen Observation & Action Log
### [Level 1] - 14:20:00
- **Screen Title:** Blender Scripting Workspace
- **Observations:** Python Interactive Console and Text Editor visible.
- **Action Taken:** `stream_file` injected train model generator code.
- **Outcome:** Script populated and executed in 3D viewport.
```

### Updating Memory via Helper:
```bash
# Initialize memory file
python3 <skill_dir>/scripts/memory_manager.py init --task "<Task Goal>"

# Log an observation and action
python3 <skill_dir>/scripts/memory_manager.py log \
  --title "Blender Scripting View" \
  --observation "Text Editor active, ready for code ingestion" \
  --action "stream_file" \
  --outcome "Injected train generator script"

# Log an obstacle and its fix
python3 <skill_dir>/scripts/memory_manager.py log \
  --title "Text Editor Ingestion" \
  --observation "Editor required focus click before streaming" \
  --obstacle "Cursor was not active in text body" \
  --solution "Clicked editor at (X:750, Y:350) before stream_file"
```

---

## 6. Long-Running Execution Discipline

1. **Continuous Screen Monitoring**:
   Do not execute blind strings of commands. At every level, capture a screenshot before and after an action to observe the screen and verify the cursor and UI state.
2. **Handle Unexpected Events**:
   If an unexpected popup, cookie dialog, or system alert appears, do not crash or abort. Perceive its close/dismiss button on the grid, click it, log the resolution in `astra_memory.md`, and resume.
3. **Calibrated Coordinates**:
   Grid labels match logical screen coordinates exactly. If an element sits halfway between `X:400` and `X:500`, its center is `450`.
4. **Verifiable Completion**:
   The agent does not stop until unambiguous visual evidence in the screenshot confirms the task is completely finished.
