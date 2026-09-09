#!/usr/bin/env python3
"""
floating_overlay.py - Non-Activating macOS Picture-in-Picture Floating Overlay HUD

Displays a live, non-intrusive floating overlay window showing Blender's viewport
(captured directly via Quartz Window Server) on top of the user's active workspace.
- Uses NSWindowStyleMaskNonactivatingPanel so it NEVER steals focus or interrupts typing.
- NSWindowCollectionBehaviorCanJoinAllSpaces so it floats across all Mission Control spaces.
- Automatically refreshes from Blender's window buffer or latest screenshot.
"""

import os
import sys
import time
import argparse

try:
    import Cocoa
    import AppKit
    from PyObjCTools import AppHelper
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


class OverlayView(AppKit.NSView):
    def initWithFrame_(self, frame):
        self = super().initWithFrame_(frame)
        if self:
            self._image = None
            self._status_text = "GPT-6 Astra • Blender Viewport Overlay"
        return self

    def setImage_(self, image):
        self._image = image
        self.setNeedsDisplay_(True)

    def setStatusText_(self, text):
        self._status_text = text
        self.setNeedsDisplay_(True)

    def drawRect_(self, dirtyRect):
        bounds = self.bounds()
        
        # Background: translucent dark glass
        AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.1, 0.12, 0.16, 0.88).set()
        path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bounds, 10.0, 10.0)
        path.fill()

        # Border
        AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.3, 0.6, 1.0, 0.5).set()
        path.setLineWidth_(1.5)
        path.stroke()

        # Draw Blender screenshot image
        if self._image:
            header_h = 24.0
            img_rect = Cocoa.NSMakeRect(
                4.0, 
                4.0, 
                bounds.size.width - 8.0, 
                bounds.size.height - header_h - 6.0
            )
            self._image.drawInRect_fromRect_operation_fraction_(
                img_rect, 
                Cocoa.NSZeroRect, 
                AppKit.NSCompositingOperationSourceOver, 
                1.0
            )

        # Header Title
        attrs = {
            AppKit.NSFontAttributeName: AppKit.NSFont.systemFontOfSize_weight_(11.0, AppKit.NSFontWeightSemibold),
            AppKit.NSForegroundColorAttributeName: AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.9, 0.95, 1.0, 0.95),
        }
        title_str = AppKit.NSAttributedString.alloc().initWithString_attributes_(self._status_text, attrs)
        title_str.drawAtPoint_(Cocoa.NSMakePoint(12.0, bounds.size.height - 20.0))


class OverlayController:
    def __init__(self, screenshot_path, width=420, height=270, refresh_interval=1.0):
        self.screenshot_path = screenshot_path
        self.width = width
        self.height = height
        self.refresh_interval = refresh_interval
        self.window = None
        self.view = None
        self.timer = None
        self.last_mtime = 0

    def setup_window(self):
        screen = AppKit.NSScreen.mainScreen()
        screen_frame = screen.visibleFrame() if screen else Cocoa.NSMakeRect(0, 0, 1470, 956)
        
        # Position at top-right corner with 20px margin
        x = screen_frame.origin.x + screen_frame.size.width - self.width - 24.0
        y = screen_frame.origin.y + screen_frame.size.height - self.height - 24.0
        frame = Cocoa.NSMakeRect(x, y, self.width, self.height)

        # Non-activating panel style mask
        style_mask = (
            AppKit.NSWindowStyleMaskTitled |
            AppKit.NSWindowStyleMaskNonactivatingPanel |
            AppKit.NSWindowStyleMaskResizable |
            AppKit.NSWindowStyleMaskFullSizeContentView
        )

        self.window = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style_mask,
            AppKit.NSBackingStoreBuffered,
            False
        )

        self.window.setTitle_("GPT-6 Astra • Blender Viewport Overlay")
        self.window.setLevel_(AppKit.NSFloatingWindowLevel)
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self.window.setHasShadow_(True)
        self.window.setTitleVisibility_(AppKit.NSWindowTitleHidden)
        self.window.setTitlebarAppearsTransparent_(True)
        self.window.setMovableByWindowBackground_(True)

        # Float across all virtual desktops / spaces and auxiliary full screens
        behavior = (
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
            AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        self.window.setCollectionBehavior_(behavior)

        self.view = OverlayView.alloc().initWithFrame_(frame)
        self.window.setContentView_(self.view)
        self.window.orderFrontRegardless()

        # Set up periodic refresh timer
        self.timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            self.refresh_interval,
            self,
            "tick:",
            None,
            True
        )
        self.update_image()

    def update_image(self):
        if not os.path.exists(self.screenshot_path):
            return
        
        try:
            mtime = os.path.getmtime(self.screenshot_path)
            if mtime > self.last_mtime:
                self.last_mtime = mtime
                ns_img = AppKit.NSImage.alloc().initWithContentsOfFile_(self.screenshot_path)
                if ns_img:
                    self.view.setImage_(ns_img)
                    self.view.setStatusText_(f"GPT-6 Astra • Live Blender ({time.strftime('%H:%M:%S')})")
        except Exception as e:
            pass

    def tick_(self, sender):
        self.update_image()


def main():
    parser = argparse.ArgumentParser(description="Non-Activating macOS Floating Overlay HUD")
    parser.add_argument("--image", default="screenshots/latest.png", help="Path to latest screenshot")
    parser.add_argument("--width", type=int, default=420, help="HUD width")
    parser.add_argument("--height", type=int, default=270, help="HUD height")
    parser.add_argument("--interval", type=float, default=0.5, help="Refresh interval in seconds")
    args = parser.parse_args()

    if not HAS_APPKIT:
        print("Error: AppKit / PyObjC not available")
        sys.exit(1)

    app = AppKit.NSApplication.sharedApplication()
    app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

    controller = OverlayController(
        screenshot_path=os.path.abspath(args.image),
        width=args.width,
        height=args.height,
        refresh_interval=args.interval
    )
    controller.setup_window()

    print(f"Floating overlay HUD started. Monitoring {args.image}...")
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
