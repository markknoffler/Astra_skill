# Long-Running Autonomous Agent Loop Specification

## The Core Perception-Action-Memory Loop

A long-running agent behaves as an autonomous control loop that maintains agency across extended horizons. The loop consists of 5 deterministic phases:

```
+-------------------------------------------------------------------------+
|                  1. ENSURE PERCEPTION DAEMON IS RUNNING                 |
|  Run: python3 screen_daemon.py status                                   |
|  If not running, start: python3 screen_daemon.py start --interval 2.0   |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                   2. PERCEIVE LATEST SCREEN STATE                       |
|  Inspect: screenshots/latest.png                                        |
|  - Check URL / window header / focused application                      |
|  - Verify current state against the task objective                      |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  3. UPDATE EPISODIC MEMORY (CWD)                        |
|  Write to astra_memory.md in working directory:                         |
|  - Log extracted text / codes / prices / states                         |
|  - Note any UI changes, unexpected modals, or errors                    |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                  4. PLAN & EXECUTE ATOMIC ACTION                        |
|  Identify target coordinates (X, Y) using grid chips & rulers           |
|  Run single atomic command, e.g.:                                       |
|    python3 mouse_action.py click --x <X> --y <Y>                        |
|    python3 mouse_action.py scroll --dy -300                             |
|    python3 keyboard_action.py type --text "search query"                |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                   5. VERIFY STATE TRANSITION                            |
|  Sleep 0.5s - 1.0s to allow UI transition                               |
|  Inspect new screenshots/latest.png:                                    |
|  - Did the screen change as expected?                                   |
|  - Did a spinner or progress bar complete?                              |
|  - If failed: Record failure in memory, adjust coordinates, retry       |
|  - If final goal achieved: Conclude and report results to user          |
+-------------------------------------------------------------------------+
```

---

## Autonomous Persistence Guidelines

1. **Never Stop on Intermediate Ambiguity**:
   If an unexpected popup (e.g. cookie consent, system alert, notification) appears, do not stop. Identify its dismiss button, click it, log the resolution in `astra_memory.md`, and resume the primary workflow.

2. **Atomic Invocations**:
   The mouse control script performs strictly **one action at a time**.
   - If you need to move the mouse and then click: run `move` then `click`, or use `click --x ... --y ...` which moves and clicks in one atomic step.
   - If you need to click multiple elements: issue sequential action commands.

3. **Verifiable Completion**:
   An agent must never declare a task complete simply because it sent mouse clicks. It must inspect `latest.png` to confirm the final visual state (e.g. "Order Confirmation #...", "Settings Saved", "Profile Updated").

4. **Handling Stalled UI**:
   - If an element doesn't respond to a single click, check `astra_memory.md` to see if a double-click or scroll was previously required.
   - Try right-click or pressing `Tab` / `Enter` via `keyboard_action.py`.
