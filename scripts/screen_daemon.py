#!/usr/bin/env python3
"""
screen_daemon.py - Continuous Autonomous Screen Perception Daemon for GPT-6 Astra Agent

Features:
- Captures screen every N seconds (default: 2.0s) autonomously.
- Overlays a subtle, non-intrusive coordinate grid showing exact logical coordinates.
- Stores screenshots in a dedicated directory:
  - screenshots/latest.png (most recent frame with grid)
  - screenshots/latest_clean.png (raw screen capture without grid)
  - screenshots/history/frame_YYYYMMDD_HHMMSS_fff.png
- Automatic rolling buffer: strictly maintains at most 50 screenshots in history,
  pruning oldest frames automatically to conserve disk space.
- Supports background daemon commands:
  - start: Start background recording daemon
  - stop: Stop running daemon
  - status: Check daemon health, latest frame, buffer size
  - capture-once: Immediate single frame capture with grid overlay
  - run: Run in foreground
"""

import os
import sys
import time
import json
import signal
import argparse
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Optional Quartz import for high-performance macOS capture
HAS_QUARTZ = False
try:
    import Quartz
    from Quartz import (
        CGWindowListCreateImage, CGRectInfinite,
        kCGWindowListOptionOnScreenOnly, kCGNullWindowID, kCGWindowImageDefault
    )
    HAS_QUARTZ = True
except ImportError:
    pass

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


def get_default_output_dir():
    """Default output directory is ../screenshots relative to script or cwd/screenshots."""
    script_dir = Path(__file__).resolve().parent.parent
    return script_dir / "screenshots"


def capture_raw_screen():
    """Captures full screen as PIL Image in RGBA format and returns (image, logical_w, logical_h)."""
    if HAS_QUARTZ:
        cg_image = CGWindowListCreateImage(
            CGRectInfinite,
            kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID,
            kCGWindowImageDefault
        )
        if cg_image is not None:
            width = Quartz.CGImageGetWidth(cg_image)
            height = Quartz.CGImageGetHeight(cg_image)
            bytes_per_row = Quartz.CGImageGetBytesPerRow(cg_image)
            pixel_data = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(cg_image))
            image = Image.frombytes("RGBA", (width, height), pixel_data, "raw", "BGRA", bytes_per_row, 1)

            if HAS_PYAUTOGUI:
                lw, lh = pyautogui.size()
            else:
                lw, lh = width, height
            return image, lw, lh

    # Fallback using PIL ImageGrab
    from PIL import ImageGrab
    image = ImageGrab.grab()
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    width, height = image.size
    if HAS_PYAUTOGUI:
        lw, lh = pyautogui.size()
    else:
        lw, lh = width, height
    return image, lw, lh


def load_font(scale, size_pt=10):
    """Attempt to load a crisp monospaced font."""
    font_paths = [
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Monaco.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    ]
    actual_size = max(9, int(size_pt * scale))
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, actual_size)
            except Exception:
                continue
    return ImageFont.load_default()


def overlay_grid(raw_image, logical_w, logical_h, grid_step=100):
    """
    Overlays a subtle, non-intrusive coordinate grid labeled in logical coordinates.
    - Minor lines every grid_step / 2
    - Major lines every grid_step
    - Coordinate labels at major intersections and screen edges
    """
    pw, ph = raw_image.size
    scale_x = pw / float(logical_w)
    scale_y = ph / float(logical_h)
    scale = (scale_x + scale_y) / 2.0

    overlay = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = load_font(scale, size_pt=10)
    small_font = load_font(scale, size_pt=8)

    # Style colors: subtle translucent lines so content beneath is completely legible
    major_line_color = (0, 200, 255, 45)      # Cyan with ~18% opacity
    minor_line_color = (255, 255, 255, 20)    # White with ~8% opacity
    chip_bg_color = (15, 23, 42, 180)         # Dark slate with ~70% opacity
    chip_text_color = (34, 211, 238, 240)     # Neon cyan
    ruler_text_color = (248, 250, 252, 230)   # Crisp off-white

    minor_step = grid_step // 2

    # Draw vertical minor lines
    for lx in range(minor_step, logical_w, minor_step):
        if lx % grid_step != 0:
            px = int(lx * scale_x)
            draw.line([(px, 0), (px, ph)], fill=minor_line_color, width=1)

    # Draw horizontal minor lines
    for ly in range(minor_step, logical_h, minor_step):
        if ly % grid_step != 0:
            py = int(ly * scale_y)
            draw.line([(0, py), (pw, py)], fill=minor_line_color, width=1)

    # Draw vertical major lines
    for lx in range(0, logical_w + 1, grid_step):
        px = int(lx * scale_x)
        draw.line([(px, 0), (px, ph)], fill=major_line_color, width=1)

    # Draw horizontal major lines
    for ly in range(0, logical_h + 1, grid_step):
        py = int(ly * scale_y)
        draw.line([(0, py), (pw, py)], fill=major_line_color, width=1)

    # Draw coordinate chips at grid intersections
    # We place badges every 200 logical points to avoid clutter, or 100 near borders
    for lx in range(0, logical_w, grid_step):
        for ly in range(0, logical_h, grid_step):
            # Place label at intersections
            px = int(lx * scale_x) + int(3 * scale)
            py = int(ly * scale_y) + int(3 * scale)
            
            # Show coordinates text
            text = f"{lx},{ly}"
            bbox = draw.textbbox((px, py), text, font=small_font)
            
            # Expand bbox slightly for padding
            pad = int(2 * scale)
            chip_box = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
            
            draw.rounded_rectangle(chip_box, radius=int(3 * scale), fill=chip_bg_color)
            draw.text((px, py), text, fill=chip_text_color, font=small_font)

    # Top ruler banner with coordinate indicators
    ruler_h = int(18 * scale)
    draw.rectangle([(0, 0), (pw, ruler_h)], fill=(10, 15, 26, 160))
    for lx in range(0, logical_w, grid_step):
        px = int(lx * scale_x)
        draw.line([(px, 0), (px, ruler_h)], fill=major_line_color, width=2)
        draw.text((px + int(4 * scale), int(2 * scale)), f"X:{lx}", fill=ruler_text_color, font=small_font)

    # Left ruler banner
    ruler_w = int(32 * scale)
    draw.rectangle([(0, ruler_h), (ruler_w, ph)], fill=(10, 15, 26, 160))
    for ly in range(grid_step, logical_h, grid_step):
        py = int(ly * scale_y)
        draw.line([(0, py), (ruler_w, py)], fill=major_line_color, width=2)
        draw.text((int(3 * scale), py + int(2 * scale)), f"Y:{ly}", fill=ruler_text_color, font=small_font)

    # Compose overlay on top of screen image
    combined = Image.alpha_composite(raw_image, overlay).convert("RGB")
    return combined


def prune_history(history_dir, max_files=50):
    """
    Maintains at most `max_files` screenshots in the history directory.
    Deletes oldest files when count exceeds `max_files`.
    """
    history_dir = Path(history_dir)
    if not history_dir.exists():
        return 0

    png_files = sorted(history_dir.glob("frame_*.png"), key=lambda p: p.stat().st_mtime)
    excess = len(png_files) - max_files
    deleted_count = 0
    if excess > 0:
        for f in png_files[:excess]:
            try:
                f.unlink()
                deleted_count += 1
            except Exception:
                pass
    return deleted_count


def do_single_capture(output_dir, max_history=50, grid_step=100):
    """Performs one capture, overlays grid, saves latest & history, prunes to 50 max."""
    output_dir = Path(output_dir)
    history_dir = output_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    raw_img, logical_w, logical_h = capture_raw_screen()
    grid_img = overlay_grid(raw_img, logical_w, logical_h, grid_step=grid_step)

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    frame_filename = f"frame_{now_str}.png"
    history_path = history_dir / frame_filename

    # Save to history
    grid_img.save(history_path, "PNG", optimize=False)

    # Atomic write to latest.png
    latest_path = output_dir / "latest.png"
    tmp_latest = output_dir / ".latest.tmp.png"
    grid_img.save(tmp_latest, "PNG")
    tmp_latest.replace(latest_path)

    # Save raw capture without grid as latest_clean.png
    latest_clean_path = output_dir / "latest_clean.png"
    tmp_clean = output_dir / ".clean.tmp.png"
    raw_img.convert("RGB").save(tmp_clean, "PNG")
    tmp_clean.replace(latest_clean_path)

    # Prune history to 50 files
    pruned = prune_history(history_dir, max_files=max_history)
    current_history_count = len(list(history_dir.glob("frame_*.png")))

    elapsed = time.time() - t0

    metadata = {
        "timestamp": datetime.now().isoformat(),
        "logical_resolution": {"width": logical_w, "height": logical_h},
        "physical_resolution": {"width": raw_img.width, "height": raw_img.height},
        "scale": round(raw_img.width / float(logical_w), 2),
        "latest_frame": str(latest_path),
        "latest_clean_frame": str(latest_clean_path),
        "history_frame": str(history_path),
        "history_count": current_history_count,
        "max_history": max_history,
        "pruned_frames": pruned,
        "capture_duration_seconds": round(elapsed, 4)
    }

    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return metadata


def daemon_loop(output_dir, interval=2.0, max_history=50, grid_step=100):
    """Main continuous daemon loop."""
    output_dir = Path(output_dir)
    pid_file = output_dir / ".screen_daemon.pid"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    def handle_exit(signum, frame):
        if pid_file.exists():
            try:
                pid_file.unlink()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    try:
        while True:
            t_start = time.time()
            try:
                do_single_capture(output_dir, max_history=max_history, grid_step=grid_step)
            except Exception as e:
                print(f"[screen_daemon] Capture error: {e}", file=sys.stderr)

            elapsed = time.time() - t_start
            sleep_time = max(0.1, interval - elapsed)
            time.sleep(sleep_time)
    finally:
        if pid_file.exists():
            try:
                pid_file.unlink()
            except Exception:
                pass


def get_running_pid(output_dir):
    pid_file = Path(output_dir) / ".screen_daemon.pid"
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        # Check if process is alive
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        # Dead or invalid PID
        try:
            pid_file.unlink()
        except Exception:
            pass
        return None


def cmd_start(args):
    output_dir = Path(args.output_dir).resolve()
    pid = get_running_pid(output_dir)
    if pid is not None:
        print(json.dumps({
            "status": "already_running",
            "pid": pid,
            "output_dir": str(output_dir)
        }, indent=2))
        return

    # Fork background process
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "daemon.log"

    import subprocess
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "run",
        "--output-dir", str(output_dir),
        "--interval", str(args.interval),
        "--max-history", str(args.max_history),
        "--grid-step", str(args.grid_step)
    ]
    
    with open(log_file, "a") as log_out:
        proc = subprocess.Popen(cmd, stdout=log_out, stderr=log_out, start_new_session=True)

    # Wait up to 2 seconds for pid file
    time.sleep(0.5)
    print(json.dumps({
        "status": "started",
        "pid": proc.pid,
        "interval_seconds": args.interval,
        "output_dir": str(output_dir),
        "log_file": str(log_file)
    }, indent=2))


def cmd_stop(args):
    output_dir = Path(args.output_dir).resolve()
    pid = get_running_pid(output_dir)
    if pid is None:
        print(json.dumps({"status": "not_running", "output_dir": str(output_dir)}, indent=2))
        return

    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.3)
        # Check if still alive
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        print(json.dumps({"status": "stopped", "pid": pid}, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    output_dir = Path(args.output_dir).resolve()
    pid = get_running_pid(output_dir)
    meta_file = output_dir / "metadata.json"
    latest_img = output_dir / "latest.png"

    metadata = None
    if meta_file.exists():
        try:
            with open(meta_file) as f:
                metadata = json.load(f)
        except Exception:
            pass

    history_dir = output_dir / "history"
    history_count = len(list(history_dir.glob("frame_*.png"))) if history_dir.exists() else 0

    print(json.dumps({
        "running": pid is not None,
        "pid": pid,
        "output_dir": str(output_dir),
        "latest_screenshot_exists": latest_img.exists(),
        "history_frames_count": history_count,
        "metadata": metadata
    }, indent=2))


def cmd_capture_once(args):
    output_dir = Path(args.output_dir).resolve()
    result = do_single_capture(output_dir, max_history=args.max_history, grid_step=args.grid_step)
    print(json.dumps({
        "status": "success",
        "action": "capture_once",
        "details": result
    }, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(
        description="Autonomous Screen Perception Daemon for GPT-6 Astra",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    default_dir = str(get_default_output_dir())

    subparsers = parser.add_subparsers(dest="command", required=True)

    # start
    p_start = subparsers.add_parser("start", help="Start continuous capture daemon in background")
    p_start.add_argument("--output-dir", default=default_dir, help="Directory to store screenshots")
    p_start.add_argument("--interval", type=float, default=2.0, help="Capture interval in seconds (default: 2.0)")
    p_start.add_argument("--max-history", type=int, default=50, help="Maximum screenshots to retain (default: 50)")
    p_start.add_argument("--grid-step", type=int, default=100, help="Logical grid step in points (default: 100)")

    # stop
    p_stop = subparsers.add_parser("stop", help="Stop running background capture daemon")
    p_stop.add_argument("--output-dir", default=default_dir)

    # status
    p_status = subparsers.add_parser("status", help="Check status of daemon and screenshot storage")
    p_status.add_argument("--output-dir", default=default_dir)

    # capture-once
    p_once = subparsers.add_parser("capture-once", help="Perform immediate single frame capture with grid")
    p_once.add_argument("--output-dir", default=default_dir)
    p_once.add_argument("--max-history", type=int, default=50)
    p_once.add_argument("--grid-step", type=int, default=100)

    # run (foreground)
    p_run = subparsers.add_parser("run", help="Run capture daemon in foreground")
    p_run.add_argument("--output-dir", default=default_dir)
    p_run.add_argument("--interval", type=float, default=2.0)
    p_run.add_argument("--max-history", type=int, default=50)
    p_run.add_argument("--grid-step", type=int, default=100)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    cmd_map = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "capture-once": cmd_capture_once,
        "run": lambda a: daemon_loop(a.output_dir, interval=a.interval, max_history=a.max_history, grid_step=a.grid_step)
    }

    handler = cmd_map.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
