"""Capture the Civ 7 game window at the OS level, independently of FireTuner.

Windows uses PrintWindow, Linux reads X11/XWayland window pixels directly, and
other platforms fall back to a screen-region grab. Linux capture does not change
focus or workspace and fails rather than capturing an unrelated desktop if the
game window cannot be read. Dependencies are listed in requirements.txt.
"""

from __future__ import annotations

import io
import sys
import time

WINDOW_TITLE_PREFIX = "Sid Meier's Civilization VII"


class ScreenshotError(Exception):
    """Raised when a screenshot cannot be captured."""


def _find_game_window():
    """Return the Civ 7 window handle, or None if not found/available.

    Matches on title prefix, not substring — editors and file managers often
    have the install path (containing "Civilization VII") in their titles.
    """
    try:
        import pygetwindow
    except (ImportError, NotImplementedError):
        return None
    candidates = [
        win for win in pygetwindow.getWindowsWithTitle(WINDOW_TITLE_PREFIX)
        if win.title.startswith(WINDOW_TITLE_PREFIX)
        and win.width > 0 and win.height > 0 and not win.isMinimized
    ]
    # The game window is titled "... (DX12)" / "... (Vulkan)"; prefer it over
    # e.g. the "... Development Tools" window, which shares the prefix
    candidates.sort(key=lambda w: 0 if "(DX" in w.title or "(Vulkan" in w.title else 1)
    return candidates[0] if candidates else None


def _capture_printwindow(hwnd):
    """Capture a window's contents via PrintWindow (Windows only).

    PW_RENDERFULLCONTENT (2) pulls DirectX/composited content, so the game
    window is captured even when occluded. Returns a PIL Image, or None if
    the capture failed or came back blank.
    """
    if sys.platform != "win32":
        return None

    import ctypes
    from ctypes import wintypes

    from PIL import Image

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        return None

    hdc_window = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    bitmap = gdi32.CreateCompatibleBitmap(hdc_window, width, height)
    img = None
    try:
        gdi32.SelectObject(hdc_mem, bitmap)
        PW_RENDERFULLCONTENT = 2
        if not user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT):
            return None

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height  # top-down rows
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0  # BI_RGB

        buf = ctypes.create_string_buffer(width * height * 4)
        DIB_RGB_COLORS = 0
        if gdi32.GetDIBits(hdc_mem, bitmap, 0, height, buf, ctypes.byref(bmi), DIB_RGB_COLORS) != height:
            return None
        img = Image.frombuffer("RGB", (width, height), buf, "raw", "BGRX", 0, 1)
    finally:
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_window)

    if img is None or img.getbbox() is None:  # all-black capture = failed
        return None
    return img


def _capture_screen_region(win):
    """Fallback: grab the screen region under the window (or primary monitor)."""
    import mss
    from PIL import Image

    if win is not None:
        try:
            win.activate()
            time.sleep(0.3)
        except Exception:
            pass  # activation is best-effort; capture whatever is there

    with mss.mss() as sct:
        if win is not None:
            monitor = {"left": win.left, "top": win.top, "width": win.width, "height": win.height}
        else:
            monitor = sct.monitors[1]
        raw = sct.grab(monitor)
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


def _capture_x11_window():
    """Capture the Civ X11/XWayland drawable without changing focus or workspace."""
    if sys.platform != "linux":
        return None

    try:
        from Xlib import X, display, error
        from PIL import Image
    except ImportError:
        return None

    xdisplay = None
    try:
        xdisplay = display.Display()
        name_atom = xdisplay.intern_atom("_NET_WM_NAME")
        utf8_atom = xdisplay.intern_atom("UTF8_STRING")
        windows = list(xdisplay.screen().root.query_tree().children)
        candidates = []

        while windows:
            window = windows.pop()
            try:
                prop = window.get_full_property(name_atom, utf8_atom)
                title = prop.value.decode("utf-8", errors="replace") if prop else ""
                if not title:
                    prop = window.get_full_property(
                        xdisplay.intern_atom("WM_NAME"), X.AnyPropertyType
                    )
                    if prop:
                        raw_title = prop.value
                        title = (
                            raw_title.decode("utf-8", errors="replace")
                            if isinstance(raw_title, bytes)
                            else str(raw_title)
                        )
                if title.startswith(WINDOW_TITLE_PREFIX):
                    candidates.append((window, title))
                windows.extend(window.query_tree().children)
            except error.XError:
                continue

        if not candidates:
            return None
        candidates.sort(
            key=lambda item: 0 if "(DX" in item[1] or "(Vulkan" in item[1] else 1
        )
        window, _title = candidates[0]
        geometry = window.get_geometry()
        if geometry.width <= 0 or geometry.height <= 0:
            return None

        attributes = window.get_attributes()
        visual = next(
            (
                visual
                for depth in xdisplay.screen().allowed_depths
                for visual in depth.visuals
                if visual.visual_id == attributes.visual
            ),
            None,
        )
        if visual is None or visual.visual_class not in (X.TrueColor, X.DirectColor):
            return None

        pixmap_format = next(
            (
                fmt
                for fmt in xdisplay.display.info.pixmap_formats
                if fmt.depth == geometry.depth
            ),
            None,
        )
        if pixmap_format is None:
            return None
        bits_per_pixel = pixmap_format.bits_per_pixel
        bytes_per_pixel = bits_per_pixel // 8
        if bits_per_pixel % 8 or bytes_per_pixel not in (3, 4):
            return None

        channel_offsets = {}
        channel_masks = {}
        for channel, mask in (
            ("R", visual.red_mask),
            ("G", visual.green_mask),
            ("B", visual.blue_mask),
        ):
            if mask == 0:
                return None
            shift = (mask & -mask).bit_length() - 1
            if (mask >> shift) != 0xFF or shift % 8:
                return None
            byte_index = shift // 8
            offset = (
                byte_index
                if xdisplay.display.info.image_byte_order == X.LSBFirst
                else bytes_per_pixel - byte_index - 1
            )
            channel_offsets[offset] = channel
            channel_masks[channel] = mask
        if len(channel_offsets) != 3:
            return None

        raw_mode = "".join(
            channel_offsets.get(index, "X") for index in range(bytes_per_pixel)
        )
        row_stride = (
            (geometry.width * bits_per_pixel + pixmap_format.scanline_pad - 1)
            // pixmap_format.scanline_pad
        ) * (pixmap_format.scanline_pad // 8)
        image_data = window.get_image(
            0, 0, geometry.width, geometry.height, X.ZPixmap, 0xFFFFFFFF
        )
        if image_data is None:
            return None
        image = Image.frombytes(
            "RGB",
            (geometry.width, geometry.height),
            image_data.data,
            "raw",
            raw_mode,
            row_stride,
            1,
        )

        if visual.visual_class == X.DirectColor:
            colormap = xdisplay.create_resource_object("colormap", attributes.colormap)
            channel_luts = {}
            for channel, mask in channel_masks.items():
                shift = (mask & -mask).bit_length() - 1
                colors = colormap.query_colors([index << shift for index in range(256)])
                component = {"R": "red", "G": "green", "B": "blue"}[channel]
                channel_luts[channel] = bytes(
                    (getattr(color, component) + 128) // 257 for color in colors
                )
            channels = list(image.split())
            for index, channel in enumerate(("R", "G", "B")):
                channels[index] = channels[index].point(channel_luts[channel])
            image = Image.merge("RGB", tuple(channels))

        return image if image.getbbox() is not None else None
    except Exception:
        return None
    finally:
        if xdisplay is not None:
            xdisplay.close()


def capture_game_window(max_width: int = 1568) -> bytes:
    """Capture the Civ 7 window and return PNG bytes.

    Uses PrintWindow on Windows and direct X11/XWayland window capture on
    Linux. Other platforms fall back to a screen-region grab. Linux raises
    ScreenshotError instead of capturing the desktop when direct capture fails.
    Downscales to max_width pixels wide (0 disables).
    """
    try:
        import mss  # noqa: F401
        from PIL import Image
    except ImportError as e:
        raise ScreenshotError(
            f"Missing dependency: {e.name}. Install with: pip install mss pygetwindow Pillow"
        ) from e

    win = _find_game_window()
    img = None
    if win is not None:
        img = _capture_printwindow(win._hWnd)
    if img is None:
        img = _capture_x11_window()
    if img is None:
        if sys.platform == "linux":
            raise ScreenshotError(
                "Could not capture the Civ 7 window through X11/XWayland"
            )
        img = _capture_screen_region(win)

    if img.getbbox() is None:
        raise ScreenshotError(
            "Screenshot was entirely black; the game window could not be captured"
        )

    if max_width and img.width > max_width:
        new_height = round(img.height * max_width / img.width)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
