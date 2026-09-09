#!/usr/bin/env python3
"""
mouse_action.py - Atomic Mouse and Screen Interaction Tool for GPT-6 Astra Agent

Executes exactly one atomic mouse action per invocation:
- move: Move cursor to (x, y)
- click: Left/right/middle click at (x, y) or current position
- right_click: Right click at (x, y)
- double_click: Double click at (x, y)
- middle_click: Middle click at (x, y)
- drag: Drag from (start_x, start_y) to (end_x, end_y)
- scroll: Scroll vertically (dy) and/or horizontally (dx)
- zoom: Zoom in (+) or zoom out (-) using modifier + scroll
- mouse_down: Press and hold a mouse button
- mouse_up: Release a mouse button
- position: Report current mouse coordinates and screen boundaries
- hover: Move to (x, y) and hover for a given duration
"""

import sys
import json
import time
import argparse
import pyautogui

# Disable PyAutoGUI failsafe to allow reaching screen corners without crash
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


def get_screen_info():
    w, h = pyautogui.size()
    pos = pyautogui.position()
    return {
        "screen_width": w,
        "screen_height": h,
        "cursor_x": pos.x,
        "cursor_y": pos.y
    }


def action_position(args):
    info = get_screen_info()
    return {
        "status": "success",
        "action": "position",
        "position": {"x": info["cursor_x"], "y": info["cursor_y"]},
        "screen": {"width": info["screen_width"], "height": info["screen_height"]}
    }


def action_move(args):
    if args.x is None or args.y is None:
        raise ValueError("move requires --x and --y coordinates")
    
    duration = args.duration if args.duration is not None else 0.1
    pyautogui.moveTo(args.x, args.y, duration=duration)
    curr = pyautogui.position()
    return {
        "status": "success",
        "action": "move",
        "target": {"x": args.x, "y": args.y},
        "actual": {"x": curr.x, "y": curr.y}
    }


def action_click(args):
    x = args.x
    y = args.y
    button = args.button or "left"
    clicks = args.clicks or 1
    interval = args.interval or 0.1

    if x is not None and y is not None:
        pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
    else:
        pyautogui.click(clicks=clicks, interval=interval, button=button)

    curr = pyautogui.position()
    return {
        "status": "success",
        "action": "click",
        "button": button,
        "clicks": clicks,
        "coordinates": {"x": curr.x, "y": curr.y}
    }


def action_right_click(args):
    args.button = "right"
    args.clicks = 1
    return action_click(args)


def action_double_click(args):
    x = args.x
    y = args.y
    button = args.button or "left"
    interval = args.interval or 0.15

    if x is not None and y is not None:
        pyautogui.doubleClick(x=x, y=y, interval=interval, button=button)
    else:
        pyautogui.doubleClick(interval=interval, button=button)

    curr = pyautogui.position()
    return {
        "status": "success",
        "action": "double_click",
        "button": button,
        "coordinates": {"x": curr.x, "y": curr.y}
    }


def action_middle_click(args):
    args.button = "middle"
    args.clicks = 1
    return action_click(args)


def action_mouse_down(args):
    button = args.button or "left"
    if args.x is not None and args.y is not None:
        pyautogui.moveTo(args.x, args.y)
    pyautogui.mouseDown(button=button)
    curr = pyautogui.position()
    return {
        "status": "success",
        "action": "mouse_down",
        "button": button,
        "coordinates": {"x": curr.x, "y": curr.y}
    }


def action_mouse_up(args):
    button = args.button or "left"
    if args.x is not None and args.y is not None:
        pyautogui.moveTo(args.x, args.y)
    pyautogui.mouseUp(button=button)
    curr = pyautogui.position()
    return {
        "status": "success",
        "action": "mouse_up",
        "button": button,
        "coordinates": {"x": curr.x, "y": curr.y}
    }


def action_drag(args):
    if args.start_x is None or args.start_y is None or args.end_x is None or args.end_y is None:
        raise ValueError("drag requires --start-x, --start-y, --end-x, and --end-y")

    duration = args.duration if args.duration is not None else 0.5
    button = args.button or "left"

    pyautogui.moveTo(args.start_x, args.start_y)
    pyautogui.dragTo(args.end_x, args.end_y, duration=duration, button=button)
    curr = pyautogui.position()
    return {
        "status": "success",
        "action": "drag",
        "from": {"x": args.start_x, "y": args.start_y},
        "to": {"x": args.end_x, "y": args.end_y},
        "button": button,
        "duration": duration,
        "actual_end": {"x": curr.x, "y": curr.y}
    }


def action_scroll(args):
    dy = args.dy or 0
    dx = args.dx or 0
    
    if args.x is not None and args.y is not None:
        pyautogui.moveTo(args.x, args.y)

    # Vertical scroll
    if dy != 0:
        pyautogui.scroll(dy)
    # Horizontal scroll (on supported platforms)
    if dx != 0:
        try:
            pyautogui.hscroll(dx)
        except AttributeError:
            pass

    curr = pyautogui.position()
    return {
        "status": "success",
        "action": "scroll",
        "dx": dx,
        "dy": dy,
        "coordinates": {"x": curr.x, "y": curr.y}
    }


def action_zoom(args):
    """Simulate zoom by holding command key (macOS) or ctrl (other) and scrolling."""
    amount = args.amount
    if amount == 0:
        raise ValueError("zoom --amount must be non-zero (positive for zoom-in, negative for zoom-out)")

    if args.x is not None and args.y is not None:
        pyautogui.moveTo(args.x, args.y)

    import platform
    modifier = "command" if platform.system() == "Darwin" else "ctrl"

    pyautogui.keyDown(modifier)
    try:
        pyautogui.scroll(amount * 3)
        time.sleep(0.05)
    finally:
        pyautogui.keyUp(modifier)

    curr = pyautogui.position()
    return {
        "status": "success",
        "action": "zoom",
        "amount": amount,
        "modifier": modifier,
        "coordinates": {"x": curr.x, "y": curr.y}
    }


def action_hover(args):
    if args.x is None or args.y is None:
        raise ValueError("hover requires --x and --y coordinates")
    
    duration = args.duration if args.duration is not None else 1.0
    pyautogui.moveTo(args.x, args.y, duration=0.1)
    time.sleep(duration)
    curr = pyautogui.position()
    return {
        "status": "success",
        "action": "hover",
        "duration": duration,
        "coordinates": {"x": curr.x, "y": curr.y}
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Atomic mouse control tool for GPT-6 Astra agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # position
    subparsers.add_parser("position", help="Report current cursor position and screen size")

    # move
    p_move = subparsers.add_parser("move", help="Move cursor to (x, y)")
    p_move.add_argument("--x", type=int, required=True, help="Target X coordinate")
    p_move.add_argument("--y", type=int, required=True, help="Target Y coordinate")
    p_move.add_argument("--duration", type=float, default=0.1, help="Movement duration in seconds")

    # click
    p_click = subparsers.add_parser("click", help="Click at (x, y) or current position")
    p_click.add_argument("--x", type=int, help="Target X coordinate (optional)")
    p_click.add_argument("--y", type=int, help="Target Y coordinate (optional)")
    p_click.add_argument("--button", choices=["left", "right", "middle"], default="left", help="Mouse button")
    p_click.add_argument("--clicks", type=int, default=1, help="Number of clicks")
    p_click.add_argument("--interval", type=float, default=0.1, help="Interval between multiple clicks")

    # right_click
    p_rc = subparsers.add_parser("right_click", help="Right click at (x, y) or current position")
    p_rc.add_argument("--x", type=int, help="Target X coordinate")
    p_rc.add_argument("--y", type=int, help="Target Y coordinate")

    # double_click
    p_dc = subparsers.add_parser("double_click", help="Double click at (x, y) or current position")
    p_dc.add_argument("--x", type=int, help="Target X coordinate")
    p_dc.add_argument("--y", type=int, help="Target Y coordinate")
    p_dc.add_argument("--button", choices=["left", "right", "middle"], default="left")
    p_dc.add_argument("--interval", type=float, default=0.15)

    # middle_click
    p_mc = subparsers.add_parser("middle_click", help="Middle click at (x, y) or current position")
    p_mc.add_argument("--x", type=int, help="Target X coordinate")
    p_mc.add_argument("--y", type=int, help="Target Y coordinate")

    # mouse_down
    p_md = subparsers.add_parser("mouse_down", help="Press and hold mouse button")
    p_md.add_argument("--x", type=int, help="Target X coordinate")
    p_md.add_argument("--y", type=int, help="Target Y coordinate")
    p_md.add_argument("--button", choices=["left", "right", "middle"], default="left")

    # mouse_up
    p_mu = subparsers.add_parser("mouse_up", help="Release mouse button")
    p_mu.add_argument("--x", type=int, help="Target X coordinate")
    p_mu.add_argument("--y", type=int, help="Target Y coordinate")
    p_mu.add_argument("--button", choices=["left", "right", "middle"], default="left")

    # drag
    p_drag = subparsers.add_parser("drag", help="Drag from (start_x, start_y) to (end_x, end_y)")
    p_drag.add_argument("--start-x", type=int, required=True, help="Start X coordinate")
    p_drag.add_argument("--start-y", type=int, required=True, help="Start Y coordinate")
    p_drag.add_argument("--end-x", type=int, required=True, help="End X coordinate")
    p_drag.add_argument("--end-y", type=int, required=True, help="End Y coordinate")
    p_drag.add_argument("--duration", type=float, default=0.5, help="Drag duration in seconds")
    p_drag.add_argument("--button", choices=["left", "right", "middle"], default="left")

    # scroll
    p_scroll = subparsers.add_parser("scroll", help="Scroll vertically or horizontally")
    p_scroll.add_argument("--dy", type=int, default=0, help="Vertical scroll (positive=up, negative=down)")
    p_scroll.add_argument("--dx", type=int, default=0, help="Horizontal scroll")
    p_scroll.add_argument("--x", type=int, help="Cursor X position before scrolling")
    p_scroll.add_argument("--y", type=int, help="Cursor Y position before scrolling")

    # zoom
    p_zoom = subparsers.add_parser("zoom", help="Zoom in (positive) or zoom out (negative)")
    p_zoom.add_argument("--amount", type=int, required=True, help="Zoom amount (e.g. 5 for zoom-in, -5 for zoom-out)")
    p_zoom.add_argument("--x", type=int, help="Cursor X position for zooming")
    p_zoom.add_argument("--y", type=int, help="Cursor Y position for zooming")

    # hover
    p_hover = subparsers.add_parser("hover", help="Hover at (x, y) for duration")
    p_hover.add_argument("--x", type=int, required=True, help="Target X coordinate")
    p_hover.add_argument("--y", type=int, required=True, help="Target Y coordinate")
    p_hover.add_argument("--duration", type=float, default=1.0, help="Hover duration in seconds")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    action_map = {
        "position": action_position,
        "move": action_move,
        "click": action_click,
        "right_click": action_right_click,
        "double_click": action_double_click,
        "middle_click": action_middle_click,
        "mouse_down": action_mouse_down,
        "mouse_up": action_mouse_up,
        "drag": action_drag,
        "scroll": action_scroll,
        "zoom": action_zoom,
        "hover": action_hover,
    }

    handler = action_map.get(args.subcommand)
    if not handler:
        print(json.dumps({"status": "error", "message": f"Unknown subcommand: {args.subcommand}"}), file=sys.stderr)
        sys.exit(1)

    try:
        result = handler(args)
        print(json.dumps(result, indent=2))
    except Exception as e:
        err_res = {"status": "error", "action": args.subcommand, "message": str(e)}
        print(json.dumps(err_res, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
