#!/usr/bin/env python3
"""
virtual_display_manager.py - Native macOS Virtual Display Controller

Creates and manages a headless virtual display on macOS using native
CoreGraphics Objective-C runtime (CGVirtualDisplay).
- Creates an isolated 1920x1080 60Hz virtual display.
- Keeps it active in a background daemon or thread.
- Provides functions to move application windows (e.g., Blender) to the virtual display.
"""

import os
import sys
import time
import json
import argparse
import signal

try:
    import objc
    from objc import lookUpClass
    import AppKit
    import ApplicationServices
    import Quartz
    HAS_OBJC = True
except ImportError:
    HAS_OBJC = False


class VirtualDisplayManager:
    def __init__(self, width=1920, height=1080, name="Astra Virtual Display"):
        self.width = width
        self.height = height
        self.name = name
        self.display = None
        self.display_id = None
        self.bounds = None

    def start(self):
        if not HAS_OBJC:
            raise RuntimeError("PyObjC / CoreGraphics not available")

        CGVirtualDisplay = lookUpClass("CGVirtualDisplay")
        CGVirtualDisplayDescriptor = lookUpClass("CGVirtualDisplayDescriptor")
        CGVirtualDisplayMode = lookUpClass("CGVirtualDisplayMode")
        CGVirtualDisplaySettings = lookUpClass("CGVirtualDisplaySettings")

        desc = CGVirtualDisplayDescriptor.alloc().init()
        desc.setName_(self.name)
        desc.setMaxPixelsWide_(self.width)
        desc.setMaxPixelsHigh_(self.height)
        desc.setSizeInMillimeters_((600, 340))
        desc.setProductID_(0x1234)
        desc.setVendorID_(0x5678)
        desc.setSerialNumber_(0x0001)

        self.display = CGVirtualDisplay.alloc().initWithDescriptor_(desc)
        if not self.display:
            raise RuntimeError("Failed to allocate CGVirtualDisplay")

        self.display_id = self.display.displayID()

        mode = CGVirtualDisplayMode.alloc().initWithWidth_height_refreshRate_(
            self.width, self.height, 60.0
        )
        settings = CGVirtualDisplaySettings.alloc().init()
        settings.setModes_([mode])
        settings.setHiDPI_(1)

        success = self.display.applySettings_(settings)
        if not success:
            raise RuntimeError("Failed to apply virtual display settings")

        time.sleep(0.5)

        # Locate virtual display screen bounds in NSScreen
        screens = AppKit.NSScreen.screens()
        for s in screens:
            desc = s.deviceDescription()
            screen_num = desc.get("NSScreenNumber")
            if screen_num == self.display_id:
                frame = s.frame()
                self.bounds = {
                    "x": int(frame.origin.x),
                    "y": int(frame.origin.y),
                    "width": int(frame.size.width),
                    "height": int(frame.size.height)
                }
                break

        if not self.bounds and len(screens) > 1:
            frame = screens[-1].frame()
            self.bounds = {
                "x": int(frame.origin.x),
                "y": int(frame.origin.y),
                "width": int(frame.size.width),
                "height": int(frame.size.height)
            }

        return {
            "status": "active",
            "display_id": self.display_id,
            "bounds": self.bounds,
            "screen_count": len(screens)
        }

    def move_window_to_display(self, pid):
        """Move the main window of a given process to the virtual display."""
        if not self.bounds:
            return False

        app = ApplicationServices.AXUIElementCreateApplication(pid)
        err, windows = ApplicationServices.AXUIElementCopyAttributeValue(app, "AXWindows", None)
        if err != 0 or not windows:
            return False

        win = windows[0]
        # Target position on the virtual screen (with 20px offset)
        target_x = float(self.bounds["x"] + 20)
        target_y = float(self.bounds["y"] + 20)
        target_w = float(self.bounds["width"] - 40)
        target_h = float(self.bounds["height"] - 40)

        # Create AXValue for position
        pos_point = Quartz.CGPoint(target_x, target_y)
        pos_val = ApplicationServices.AXValueCreate(
            ApplicationServices.kAXValueCGPointType, pos_point
        )
        ApplicationServices.AXUIElementSetAttributeValue(win, "AXPosition", pos_val)

        # Create AXValue for size
        size_val = ApplicationServices.AXValueCreate(
            ApplicationServices.kAXValueCGSizeType,
            Quartz.CGSize(target_w, target_h)
        )
        ApplicationServices.AXUIElementSetAttributeValue(win, "AXSize", size_val)

        return True


def run_daemon():
    mgr = VirtualDisplayManager()
    info = mgr.start()
    print(json.dumps(info, indent=2))
    sys.stdout.flush()

    # Move Blender if running
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID
    )
    blender_pid = None
    for w in windows:
        if "blender" in w.get("kCGWindowOwnerName", "").lower() and w.get("kCGWindowBounds", {}).get("Height", 0) > 400:
            blender_pid = w.get("kCGWindowOwnerPID")
            break

    if blender_pid:
        moved = mgr.move_window_to_display(blender_pid)
        print(f"Blender (PID {blender_pid}) moved to virtual display: {moved}")
        sys.stdout.flush()

    # Keep alive until SIGTERM / SIGINT
    stop_event = False
    def handle_sig(sig, frame):
        nonlocal stop_event
        stop_event = True

    signal.signal(signal.SIGINT, handle_sig)
    signal.signal(signal.SIGTERM, handle_sig)

    while not stop_event:
        time.sleep(1.0)

    print("Virtual display daemon shutting down...")


if __name__ == "__main__":
    run_daemon()
