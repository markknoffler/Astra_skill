#!/usr/bin/env python3
"""
memory_manager.py - Persistent Working-Directory Memory Tracker for GPT-6 Astra

Maintains a rich, persistent Markdown episodic memory file (`astra_memory.md`)
in the agent's current working directory (CWD), distinct from the skills directory.

Why this exists:
The screen daemon strictly caps screenshot history at 50 frames to prevent disk exhaustion.
Therefore, all visual observations, extracted information, UI quirks, navigation paths,
coordinates used, and resolved bugs must be recorded in this Markdown ledger so future steps
or resumed agent runs have complete, permanent task memory.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

MEMORY_FILENAME = "astra_memory.md"


def get_memory_file_path(cwd=None):
    base_dir = Path(cwd).resolve() if cwd else Path.cwd()
    return base_dir / MEMORY_FILENAME


def init_memory_file(task_description, target_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"""# GPT-6 Astra Task Memory & Screen Journal

**Initialized:** {now}  
**Working Directory:** `{target_path.parent}`  
**Primary Goal:** {task_description}

---

## Task Overview & Progress State
- **Status:** In Progress
- **Current Subgoal:** Initial perception and orientation
- **Total Screens Observed:** 0
- **Actions Executed:** 0

---

## Critical Extracted Information & Entity Vault
> Permanent store for text, credentials, confirmation IDs, form fields, and data
> extracted from screenshots that are needed later in the task.

*(No critical entities extracted yet)*

---

## Navigation Obstacles, UI Quirks & Resolution Log
> Detailed record of navigation hurdles, misclicks, unresponsive elements, or unexpected
> popups, along with the exact coordinates and remedies used to overcome them.

*(No obstacles encountered yet)*

---

## Chronological Screen Observation & Action Log

"""
    target_path.write_text(content, encoding="utf-8")
    return {
        "status": "initialized",
        "file": str(target_path),
        "goal": task_description
    }


def log_screen_event(args):
    target_path = get_memory_file_path(args.cwd)
    if not target_path.exists():
        init_memory_file(args.task or "Autonomous Screen Control Task", target_path)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    coords_str = f"({args.x}, {args.y})" if args.x is not None and args.y is not None else "N/A"

    entry = f"""
### [Screen Event] - {now}
- **Screen / View Title:** {args.title}
- **Visual Observations:** {args.observation}
- **Extracted Information:** {args.extracted or "None"}
- **Action Taken:** `{args.action or "Observe / None"}` at coordinates `{coords_str}`
- **Outcome / Visual Feedback:** {args.outcome or "Pending next frame verification"}
"""
    if args.obstacle:
        entry += f"- **⚠️ Obstacle / Bug Encountered:** {args.obstacle}\n"
    if args.solution:
        entry += f"- **✅ Solution / Recovery Applied:** {args.solution}\n"

    entry += "\n"

    # Also update Entity Vault if critical info was provided
    content = target_path.read_text(encoding="utf-8")
    if args.entity_key and args.entity_value:
        entity_line = f"- **{args.entity_key}:** `{args.entity_value}` (captured at {now})\n"
        vault_marker = "*(No critical entities extracted yet)*\n"
        if vault_marker in content:
            content = content.replace(vault_marker, entity_line)
        else:
            insert_pos = content.find("## Navigation Obstacles")
            if insert_pos != -1:
                content = content[:insert_pos] + entity_line + "\n" + content[insert_pos:]

    # Also update Obstacle section if an obstacle was noted
    if args.obstacle and args.solution:
        obs_entry = f"- **Issue at '{args.title}':** {args.obstacle}\n  - **Fix:** {args.solution} (Coords: `{coords_str}`)\n"
        obs_marker = "*(No obstacles encountered yet)*\n"
        if obs_marker in content:
            content = content.replace(obs_marker, obs_entry)
        else:
            insert_pos = content.find("## Chronological Screen Observation")
            if insert_pos != -1:
                content = content[:insert_pos] + obs_entry + "\n" + content[insert_pos:]

    # Append entry at the end
    content += entry
    target_path.write_text(content, encoding="utf-8")

    return {
        "status": "logged",
        "file": str(target_path),
        "timestamp": now,
        "title": args.title,
        "action": args.action,
        "coords": coords_str
    }


def read_memory(cwd=None):
    target_path = get_memory_file_path(cwd)
    if not target_path.exists():
        return {"status": "not_found", "file": str(target_path)}
    return {
        "status": "found",
        "file": str(target_path),
        "content": target_path.read_text(encoding="utf-8")
    }


def build_parser():
    parser = argparse.ArgumentParser(description="Persistent task memory manager for GPT-6 Astra agent")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Initialize a new astra_memory.md in current directory")
    p_init.add_argument("--task", required=True, help="Task description or goal")
    p_init.add_argument("--cwd", default=None, help="Working directory path (default: current directory)")

    # log
    p_log = subparsers.add_parser("log", help="Log a screen observation and action")
    p_log.add_argument("--title", required=True, help="Short title of the current window or screen state")
    p_log.add_argument("--observation", required=True, help="What was observed on the screen")
    p_log.add_argument("--extracted", help="Any critical text, IDs, or info extracted from the screen")
    p_log.add_argument("--action", help="Action performed (e.g. click, scroll, move, type)")
    p_log.add_argument("--x", type=int, help="Target X coordinate clicked/moved to")
    p_log.add_argument("--y", type=int, help="Target Y coordinate clicked/moved to")
    p_log.add_argument("--outcome", help="Observed result or state change")
    p_log.add_argument("--obstacle", help="Any bug, error, misclick or UI issue encountered")
    p_log.add_argument("--solution", help="How the obstacle was or will be overcome")
    p_log.add_argument("--entity-key", help="Key name for permanent entity storage")
    p_log.add_argument("--entity-value", help="Value for permanent entity storage")
    p_log.add_argument("--task", help="Task description (if initializing)")
    p_log.add_argument("--cwd", default=None, help="Working directory path")

    # read
    p_read = subparsers.add_parser("read", help="Read current task memory")
    p_read.add_argument("--cwd", default=None)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.subcommand == "init":
        target = get_memory_file_path(args.cwd)
        res = init_memory_file(args.task, target)
        print(json.dumps(res, indent=2))
    elif args.subcommand == "log":
        res = log_screen_event(args)
        print(json.dumps(res, indent=2))
    elif args.subcommand == "read":
        res = read_memory(args.cwd)
        if res["status"] == "found":
            print(res["content"])
        else:
            print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
