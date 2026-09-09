#!/usr/bin/env python3
"""
screen_capture.py - Model-Driven Screen Perception Tool for GPT-6 Astra Agent

Takes an on-demand screenshot whenever the AI agent decides to inspect the screen:
- Captures the active display using native macOS Quartz / PyAutoGUI.
- Overlays a subtle, non-intrusive coordinate grid labeled in logical screen points.
- Saves:
  - screenshots/latest.png (most recent frame with coordinate grid for targeting)
  - screenshots/latest_clean.png (raw screen capture without grid)
  - screenshots/history/frame_YYYYMMDD_HHMMSS_fff.png
- Strictly maintains a 50-screenshot FIFO rolling buffer (deleting oldest frames).
- Outputs a JSON summary with logical dimensions, scale, and exact file paths.
"""

import os
import sys
import time
import json
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
    script_dir = Path(__file__).resolve().parent.parent
    return script_dir / "screenshots"


def find_app_window(app_name):
    """Finds the main window ID, bounds, and title for a named application."""
    if not HAS_QUARTZ:
        return None
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID
    )
    best_w = None
    max_area = 0
    for w in windows:
        owner = w.get('kCGWindowOwnerName', '')
        if app_name.lower() in owner.lower():
            bounds = w.get('kCGWindowBounds', {})
            width = bounds.get('Width', 0)
            height = bounds.get('Height', 0)
            area = width * height
            # Filter out menubar/status bar items (usually small heights)
            if area > max_area and height > 100 and width > 200:
                max_area = area
                best_w = {
                    'id': w.get('kCGWindowNumber'),
                    'name': w.get('kCGWindowName', ''),
                    'owner': owner,
                    'bounds': bounds,
                    'logical_w': int(width),
                    'logical_h': int(height)
                }
    return best_w


def capture_raw_screen(target_app=None):
    """
    Captures either full screen or a specific application window as PIL Image in RGBA.
    Targeting an app window allows perception even when the user is on other screens
    or working in different foreground applications.
    """
    if target_app and HAS_QUARTZ:
        win_info = find_app_window(target_app)
        if win_info:
            cg_image = Quartz.CGWindowListCreateImage(
                Quartz.CGRectNull,
                Quartz.kCGWindowListOptionIncludingWindow,
                win_info['id'],
                Quartz.kCGWindowImageBoundsIgnoreFraming
            )
            if cg_image is not None:
                width = Quartz.CGImageGetWidth(cg_image)
                height = Quartz.CGImageGetHeight(cg_image)
                bytes_per_row = Quartz.CGImageGetBytesPerRow(cg_image)
                pixel_data = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(cg_image))
                image = Image.frombytes("RGBA", (width, height), pixel_data, "raw", "BGRA", bytes_per_row, 1)
                return image, win_info['logical_w'], win_info['logical_h'], win_info

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
            return image, lw, lh, None

    # Fallback to PIL ImageGrab
    from PIL import ImageGrab
    image = ImageGrab.grab()
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    width, height = image.size
    if HAS_PYAUTOGUI:
        lw, lh = pyautogui.size()
    else:
        lw, lh = width, height
    return image, lw, lh, None


def load_font(scale, size_pt=10):
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
    - Subtle translucent lines (never obscuring underlying UI elements)
    - Coordinate chips (X, Y) at grid intersections
    - Top & left edge rulers
    """
    pw, ph = raw_image.size
    scale_x = pw / float(logical_w)
    scale_y = ph / float(logical_h)
    scale = (scale_x + scale_y) / 2.0

    overlay = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = load_font(scale, size_pt=10)
    small_font = load_font(scale, size_pt=8)

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

    # Draw coordinate badges at major intersections
    for lx in range(0, logical_w, grid_step):
        for ly in range(0, logical_h, grid_step):
            px = int(lx * scale_x) + int(3 * scale)
            py = int(ly * scale_y) + int(3 * scale)
            text = f"{lx},{ly}"
            bbox = draw.textbbox((px, py), text, font=small_font)
            pad = int(2 * scale)
            chip_box = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
            draw.rounded_rectangle(chip_box, radius=int(3 * scale), fill=chip_bg_color)
            draw.text((px, py), text, fill=chip_text_color, font=small_font)

    # Top ruler
    ruler_h = int(18 * scale)
    draw.rectangle([(0, 0), (pw, ruler_h)], fill=(10, 15, 26, 160))
    for lx in range(0, logical_w, grid_step):
        px = int(lx * scale_x)
        draw.line([(px, 0), (px, ruler_h)], fill=major_line_color, width=2)
        draw.text((px + int(4 * scale), int(2 * scale)), f"X:{lx}", fill=ruler_text_color, font=small_font)

    # Left ruler
    ruler_w = int(32 * scale)
    draw.rectangle([(0, ruler_h), (ruler_w, ph)], fill=(10, 15, 26, 160))
    for ly in range(grid_step, logical_h, grid_step):
        py = int(ly * scale_y)
        draw.line([(0, py), (ruler_w, py)], fill=major_line_color, width=2)
        draw.text((int(3 * scale), py + int(2 * scale)), f"Y:{ly}", fill=ruler_text_color, font=small_font)

    combined = Image.alpha_composite(raw_image, overlay).convert("RGB")
    return combined


def prune_history(history_dir, max_files=50):
    """Retains strictly up to max_files in history, deleting older ones."""
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


def capture(output_dir=None, grid_step=100, max_history=50, target_app=None):
    """Executes a capture and saves latest and history frames."""
    if output_dir is None:
        output_dir = get_default_output_dir()
    output_dir = Path(output_dir)
    history_dir = output_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    raw_img, logical_w, logical_h, win_info = capture_raw_screen(target_app=target_app)
    grid_img = overlay_grid(raw_img, logical_w, logical_h, grid_step=grid_step)

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    frame_filename = f"frame_{now_str}.png"
    history_path = history_dir / frame_filename

    # Save timestamped history frame
    grid_img.save(history_path, "PNG", optimize=False)

    # Save latest with grid
    latest_path = output_dir / "latest.png"
    tmp_latest = output_dir / ".latest.tmp.png"
    grid_img.save(tmp_latest, "PNG")
    tmp_latest.replace(latest_path)

    # Save latest raw without grid
    latest_clean_path = output_dir / "latest_clean.png"
    tmp_clean = output_dir / ".clean.tmp.png"
    raw_img.convert("RGB").save(tmp_clean, "PNG")
    tmp_clean.replace(latest_clean_path)

    # Rolling buffer: Prune history to max 50 screenshots
    pruned = prune_history(history_dir, max_files=max_history)
    current_count = len(list(history_dir.glob("frame_*.png")))

    elapsed = round(time.time() - t0, 4)

    result = {
        "status": "success",
        "action": "screen_capture",
        "target_app": target_app if win_info else None,
        "window_id": win_info["id"] if win_info else None,
        "window_name": win_info["name"] if win_info else None,
        "timestamp": datetime.now().isoformat(),
        "logical_resolution": {"width": logical_w, "height": logical_h},
        "physical_resolution": {"width": raw_img.width, "height": raw_img.height},
        "scale": round(raw_img.width / float(logical_w), 2),
        "latest_screenshot": str(latest_path),
        "latest_clean_screenshot": str(latest_clean_path),
        "history_screenshot": str(history_path),
        "history_frames_count": current_count,
        "max_history": max_history,
        "pruned_frames": pruned,
        "duration_seconds": elapsed
    }

    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Model-driven on-demand screen capture for GPT-6 Astra")
    parser.add_argument("--output-dir", default=None, help="Directory to save screenshots")
    parser.add_argument("--grid-step", type=int, default=100, help="Logical grid step size (default: 100)")
    parser.add_argument("--max-history", type=int, default=50, help="Max screenshots retained in buffer (default: 50)")
    parser.add_argument("--app", default=None, help="Capture a specific application window by name (e.g. Blender) even when backgrounded or on another desktop space")

    args = parser.parse_args()
    res = capture(output_dir=args.output_dir, grid_step=args.grid_step, max_history=args.max_history, target_app=args.app)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
