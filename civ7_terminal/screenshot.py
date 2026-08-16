"""Capture screenshots of the Civ 7 game window (OS-level, not via the debug port).

The FireTuner protocol is text-only, so screenshots are taken by capturing the
game window contents. On Windows this uses PrintWindow with PW_RENDERFULLCONTENT,
which reads the window straight from the compositor — the shot comes out clean
even when other windows overlap the game. Falls back to a screen-region grab
(mss) if that fails. Requires mss, pygetwindow, and Pillow (see requirements.txt).
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
    except ImportError:
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


def capture_game_window(max_width: int = 1568) -> bytes:
    """Capture the Civ 7 window and return PNG bytes.

    Prefers an occlusion-proof PrintWindow capture; falls back to a screen
    grab of the window region, then the primary monitor. Downscales to
    max_width pixels wide (0 disables).
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
        img = _capture_screen_region(win)

    if max_width and img.width > max_width:
        new_height = round(img.height * max_width / img.width)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
