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
    """Resize and pad a screenshot to a square to reduce token usage and preserve aspect ratio.

    Pads the image to a square with a white background, scales it to max_size,
    and encodes as JPEG with quality=85 for compression.

    Args:
        png_bytes: Raw PNG screenshot bytes from ADB.
        max_size: Maximum dimension (square edge) in pixels. Default 1024.

    Returns:
        Compressed JPEG bytes.
    """
    img = Image.open(io.BytesIO(png_bytes))
    w, h = img.size

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    max_dim = max(w, h)
    square_img = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
    offset_x = (max_dim - w) // 2
    offset_y = (max_dim - h) // 2
    square_img.paste(img, (offset_x, offset_y))

    if max_dim > max_size:
        square_img = square_img.resize((max_size, max_size), Image.LANCZOS)

    buf = io.BytesIO()
    square_img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
