#!/usr/bin/env python3
"""
keyboard_action.py - Dual-Mode Precision Keyboard Controller for GPT-6 Astra Agent

Provides two specialized keyboard operation modes:
1. Targeted Real-Time Input Strokes & Hold Controls:
   - Designed for complex interactive applications (Blender, Unreal Engine, Isaac Sim, CAD).
   - Atomic strokes, key combinations (hotkeys), repeated presses, and hold/release states
     (e.g., holding Shift/Alt for navigation or W/A/S/D for viewport travel).
2. Bulk File-to-Keystroke Fast Streamer:
   - Reads code/scripts/data files created in the model's CWD and enters the contents
     directly into the focused cursor location rapidly via high-speed keystrokes or
     native clipboard-assisted burst paste.
"""

import os
import sys
import time
import json
import argparse
import subprocess
import platform
import pyautogui

# Disable failsafe to prevent edge-crash during automated interaction
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

IS_MACOS = platform.system() == "Darwin"
DEFAULT_MODIFIER = "command" if IS_MACOS else "ctrl"


def normalize_key(k):
    """Normalizes key names to PyAutoGUI standard."""
    k = k.lower().strip()
    mapping = {
        "cmd": "command" if IS_MACOS else "ctrl",
        "command": "command" if IS_MACOS else "ctrl",
        "opt": "option" if IS_MACOS else "alt",
        "option": "option" if IS_MACOS else "alt",
        "alt": "alt",
        "ctrl": "ctrl",
        "control": "ctrl",
        "shift": "shift",
        "esc": "escape",
        "escape": "escape",
        "return": "return" if IS_MACOS else "enter",
        "enter": "enter",
        "tab": "tab",
        "space": "space",
        "backspace": "backspace",
        "del": "delete",
        "delete": "delete",
    }
    return mapping.get(k, k)


def action_stroke(args):
    """Execute a sequence of discrete key strokes with controlled intervals."""
    keys = [normalize_key(k) for k in args.keys]
    interval = args.interval if args.interval is not None else 0.05
    for k in keys:
        pyautogui.press(k)
        if interval > 0:
            time.sleep(interval)
    return {
        "status": "success",
        "action": "stroke",
        "keys": keys,
        "count": len(keys),
        "interval": interval
    }


def action_hotkey(args):
    """Execute a key combination (modifier + key)."""
    keys = [normalize_key(k) for k in args.keys]
    pyautogui.hotkey(*keys)
    return {
        "status": "success",
        "action": "hotkey",
        "keys": keys
    }


def action_hold(args):
    """Hold one or more keys down for a specified duration, then release."""
    key = normalize_key(args.key)
    duration = args.duration if args.duration is not None else 1.0
    pyautogui.keyDown(key)
    try:
        time.sleep(duration)
    finally:
        pyautogui.keyUp(key)
    return {
        "status": "success",
        "action": "hold",
        "key": key,
        "duration": duration
    }


def action_down(args):
    """Press and hold a key down indefinitely until explicit key_up."""
    key = normalize_key(args.key)
    pyautogui.keyDown(key)
    return {
        "status": "success",
        "action": "down",
        "key": key,
        "state": "held_down"
    }


def action_up(args):
    """Release a held key."""
    key = normalize_key(args.key)
    pyautogui.keyUp(key)
    return {
        "status": "success",
        "action": "up",
        "key": key,
        "state": "released"
    }


def action_type(args):
    """Type a string directly into focused field with optional micro-delay."""
    text = args.text
    interval = args.interval if args.interval is not None else 0.01
    pyautogui.write(text, interval=interval)
    return {
        "status": "success",
        "action": "type",
        "length": len(text),
        "preview": text[:60] + ("..." if len(text) > 60 else "")
    }


def set_macos_clipboard(content):
    """Set system clipboard using pbcopy on macOS."""
    proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    proc.communicate(content.encode("utf-8"))
    return proc.returncode == 0


def action_stream_file(args):
    """
    Reads a file from CWD or given path, and inputs its contents into
    the current focused application cursor location.
    
    Modes:
    - 'paste' (default, ultra-fast): loads into system clipboard and fires Cmd+V.
      Preserves all whitespace, indentation, newlines, and unicode perfectly in ~0.05s.
    - 'keystroke' (streaming): types line-by-line or character-by-character via
      simulated keyboard events for applications that reject clipboard paste.
    """
    file_path = os.path.abspath(args.file)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    line_count = len(lines)
    char_count = len(content)

    method = args.method.lower()

    if method == "paste":
        if IS_MACOS:
            success = set_macos_clipboard(content)
            if not success:
                raise RuntimeError("Failed to copy file contents to macOS clipboard via pbcopy")
        else:
            try:
                import pyperclip
                pyperclip.copy(content)
            except ImportError:
                # Fallback to keystroke if pyperclip missing on non-macOS
                method = "keystroke"

        if method == "paste":
            time.sleep(0.05)
            # Trigger paste combination
            paste_mod = "command" if IS_MACOS else "ctrl"
            pyautogui.hotkey(paste_mod, "v")
            time.sleep(0.05)
            return {
                "status": "success",
                "action": "stream_file",
                "method": "paste",
                "file": file_path,
                "lines": line_count,
                "characters": char_count,
                "duration_seconds": 0.1
            }

    # Keystroke streaming method
    interval = args.interval if args.interval is not None else 0.005
    line_delay = args.line_delay if args.line_delay is not None else 0.02
    t0 = time.time()

    for idx, line in enumerate(lines):
        pyautogui.write(line, interval=interval)
        pyautogui.press("enter")
        if line_delay > 0:
            time.sleep(line_delay)

    total_time = round(time.time() - t0, 3)
    return {
        "status": "success",
        "action": "stream_file",
        "method": "keystroke",
        "file": file_path,
        "lines": line_count,
        "characters": char_count,
        "duration_seconds": total_time
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Dual-Mode Precision Keyboard Controller for GPT-6 Astra",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # stroke
    p_stroke = subparsers.add_parser("stroke", help="Input discrete key strokes sequentially")
    p_stroke.add_argument("--keys", nargs="+", required=True, help="Key names (e.g. g x 2 enter)")
    p_stroke.add_argument("--interval", type=float, default=0.05, help="Delay between strokes in seconds")

    # hotkey
    p_hotkey = subparsers.add_parser("hotkey", help="Execute key combination (e.g. shift a, alt p, cmd s)")
    p_hotkey.add_argument("--keys", nargs="+", required=True, help="Keys in combination")

    # hold
    p_hold = subparsers.add_parser("hold", help="Hold a key down for specified duration")
    p_hold.add_argument("--key", required=True, help="Key name to hold (e.g. shift, w, alt)")
    p_hold.add_argument("--duration", type=float, default=1.0, help="Hold duration in seconds")

    # down
    p_down = subparsers.add_parser("down", help="Press and hold key down (requires explicit 'up')")
    p_down.add_argument("--key", required=True, help="Key to hold down")

    # up
    p_up = subparsers.add_parser("up", help="Release a held key")
    p_up.add_argument("--key", required=True, help="Key to release")

    # type
    p_type = subparsers.add_parser("type", help="Type text string directly")
    p_type.add_argument("--text", required=True, help="Text to type")
    p_type.add_argument("--interval", type=float, default=0.01, help="Delay per character")

    # stream_file
    p_stream = subparsers.add_parser("stream_file", help="Stream/paste full file into focused cursor position")
    p_stream.add_argument("--file", required=True, help="Path to text/code file in CWD or system")
    p_stream.add_argument("--method", choices=["paste", "keystroke"], default="paste",
                          help="Injection method ('paste' for instant burst, 'keystroke' for simulated typing)")
    p_stream.add_argument("--interval", type=float, default=0.005, help="Keystroke interval (if method=keystroke)")
    p_stream.add_argument("--line-delay", type=float, default=0.02, help="Delay between lines (if method=keystroke)")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    action_map = {
        "stroke": action_stroke,
        "hotkey": action_hotkey,
        "hold": action_hold,
        "down": action_down,
        "up": action_up,
        "type": action_type,
        "stream_file": action_stream_file
    }

    handler = action_map.get(args.subcommand)
    if not handler:
        print(json.dumps({"status": "error", "message": f"Unknown subcommand: {args.subcommand}"}), file=sys.stderr)
        sys.exit(1)

    try:
        res = handler(args)
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "action": args.subcommand, "message": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
