"""Screen capture and image processing utilities for ADB agent."""

import io
import subprocess

from PIL import Image


def take_screenshot() -> bytes:
    """Capture the current phone screen via ADB and return raw PNG bytes."""
    result = subprocess.run(
        ["adb", "exec-out", "screencap", "-p"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"adb screencap failed: {result.stderr.decode()}")
    return result.stdout


def get_screen_size() -> dict:
    """Get the physical screen resolution of the connected Android device.

    Returns:
        dict: {"width": int, "height": int} representing the screen dimensions in pixels.
    """
    result = subprocess.run(
        ["adb", "shell", "wm", "size"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": f"Failed to get screen size: {result.stderr}"}

    # Output format: "Physical size: 1080x2400"
    for line in result.stdout.strip().splitlines():
        if "Physical size" in line or "Override size" in line:
            size_str = line.split(":")[-1].strip()
            w, h = size_str.split("x")
            return {"width": int(w), "height": int(h)}

    return {"status": "error", "error_message": f"Could not parse screen size from: {result.stdout}"}


def resize_screenshot(png_bytes: bytes, max_size: int = 640) -> bytes:
    """Resize a screenshot to reduce token usage when sending to LLM.

    Preserves aspect ratio, scales the long edge to max_size pixels,
    and encodes as JPEG with quality=85 for compression.

    Args:
        png_bytes: Raw PNG screenshot bytes from ADB.
        max_size: Maximum dimension (long edge) in pixels. Default 640.

    Returns:
        Compressed JPEG bytes.
    """
    img = Image.open(io.BytesIO(png_bytes))
    w, h = img.size

    # Scale so the long edge equals max_size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    # Convert to RGB (JPEG doesn't support alpha)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
