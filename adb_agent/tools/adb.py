"""ADB interaction tools for controlling the Android device, screen capture, and file ops.

All coordinate parameters (x, y) use Gemini's 0-1000 normalized coordinate
system. Internally, they are converted to real screen pixels via:
    real_x = norm_x * screen_width / 1000
"""

import base64
import io
import subprocess
import time

from PIL import Image

# Cache for physical screen dimensions
# (Removed, no longer needed)


def check_adb_connection() -> dict:
    """Check if an Android device is connected via ADB and reachable.

    Returns:
        dict with status, message, and device info if connected.
    """
    result = subprocess.run(
        ["adb", "devices"],
        capture_output=True,
        text=True,
    )
    
    lines = result.stdout.strip().splitlines()
    # First line is usually "List of devices attached"
    devices = [line.split()[0] for line in lines[1:] if "device" in line and "offline" not in line]
    
    if not devices:
        return {
            "status": "error", 
            "error_message": "No ADB devices connected or device is offline. Please check USB debugging and connection."
        }
        
    return {
        "status": "success", 
        "message": f"Connected to device: {devices[0]}",
        "devices": devices
    }


import re

def _get_screen_dimensions() -> tuple[int, int]:
    """Get current screen dimensions, accounting for device rotation."""
    result = subprocess.run(
        ["adb", "shell", "dumpsys", "window", "displays"],
        capture_output=True,
        text=True,
    )
    
    # Look for "cur=1080x2400" or similar in the output
    match = re.search(r"cur=(\d+)x(\d+)", result.stdout)
    if match:
        return int(match.group(1)), int(match.group(2))
        
    # Fallback to wm size if dumpsys window fails
    result = subprocess.run(
        ["adb", "shell", "wm", "size"],
        capture_output=True,
        text=True,
    )
    for line in result.stdout.strip().splitlines():
        if "Physical size" in line or "Override size" in line:
            size_str = line.split(":")[-1].strip()
            w, h = size_str.split("x")
            return int(w), int(h)

    raise RuntimeError(f"Could not parse screen size from dumpsys or wm size.")


def _to_real_coords(norm_x: int, norm_y: int) -> tuple[int, int]:
    """Convert 0-1000 normalized coordinates to real screen pixels.
    
    The LLM sees a 1:1 padded screenshot where the original screen is CENTERED.
    Therefore, the 0-1000 coordinate system maps to a max(w, h) x max(w, h) area.
    """
    w, h = _get_screen_dimensions()
    max_dim = max(w, h)
    
    # Calculate pixel coordinate in the padded max_dim x max_dim image
    pad_x = norm_x * max_dim / 1000.0
    pad_y = norm_y * max_dim / 1000.0
    
    # Calculate padding offsets
    offset_x = (max_dim - w) / 2.0
    offset_y = (max_dim - h) / 2.0
    
    # Subtract offsets to get real screen coordinates
    real_x = int(pad_x - offset_x)
    real_y = int(pad_y - offset_y)
    
    # Clamp to actual screen bounds just in case the LLM clicks on the white padding
    real_x = max(0, min(real_x, w - 1))
    real_y = max(0, min(real_y, h - 1))
    
    return real_x, real_y


def adb_shell(command: str, purpose: str = "") -> dict:
    """Execute an arbitrary ADB shell command on the device.

    Use this for actions not covered by other tools: launching/stopping apps,
    opening URLs, querying device state, managing files, etc.
    Example: adb_shell('am start -a android.intent.action.VIEW -d https://google.com')

    Args:
        command: Shell command string to run on the device.
        purpose: Why are you executing this command? What is the expected outcome?

    Returns:
        dict with status, stdout output, stderr, and returncode.
    """
    result = subprocess.run(
        ["adb", "shell", command],
        capture_output=True,
        text=True,
    )
    return {
        "status": "success" if result.returncode == 0 else "error",
        "output": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
    }


def tap(x: int, y: int, purpose: str = "") -> dict:
    """Tap a point on the screen.

    Args:
        x: Horizontal coordinate in 0-1000 range (0=left, 1000=right).
        y: Vertical coordinate in 0-1000 range (0=top, 1000=bottom).
        purpose: Why are you tapping here? What element are you trying to interact with?

    Returns:
        dict with status and message.
    """
    real_x, real_y = _to_real_coords(x, y)
    result = subprocess.run(
        ["adb", "shell", "input", "tap", str(real_x), str(real_y)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": f"Tapped at ({x}, {y}) -> real ({real_x}, {real_y})"}


def long_press(x: int, y: int, duration_ms: int = 1000, purpose: str = "") -> dict:
    """Long press a point on the screen.

    Args:
        x: Horizontal coordinate in 0-1000 range.
        y: Vertical coordinate in 0-1000 range.
        duration_ms: Press duration in milliseconds. Default 1000ms.
        purpose: Why are you long pressing here?

    Returns:
        dict with status and message.
    """
    real_x, real_y = _to_real_coords(x, y)
    result = subprocess.run(
        ["adb", "shell", "input", "swipe",
         str(real_x), str(real_y), str(real_x), str(real_y), str(duration_ms)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": f"Long pressed at ({x}, {y}) for {duration_ms}ms"}


def double_tap(x: int, y: int, purpose: str = "") -> dict:
    """Double tap a point on the screen.

    Args:
        x: Horizontal coordinate in 0-1000 range.
        y: Vertical coordinate in 0-1000 range.
        purpose: Why are you double tapping here?

    Returns:
        dict with status and message.
    """
    real_x, real_y = _to_real_coords(x, y)
    subprocess.run(
        ["adb", "shell", "input", "tap", str(real_x), str(real_y)],
        capture_output=True,
    )
    time.sleep(0.1)
    subprocess.run(
        ["adb", "shell", "input", "tap", str(real_x), str(real_y)],
        capture_output=True,
    )
    return {"status": "success", "message": f"Double tapped at ({x}, {y})"}


def swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300, purpose: str = "") -> dict:
    """Swipe from one point to another on the screen.

    Args:
        start_x: Start horizontal coordinate in 0-1000 range.
        start_y: Start vertical coordinate in 0-1000 range.
        end_x: End horizontal coordinate in 0-1000 range.
        end_y: End vertical coordinate in 0-1000 range.
        duration_ms: Swipe duration in milliseconds. Default 300ms.
        purpose: Why are you swiping? (e.g., "scroll down to see more items")

    Returns:
        dict with status and message.
    """
    sx, sy = _to_real_coords(start_x, start_y)
    ex, ey = _to_real_coords(end_x, end_y)
    result = subprocess.run(
        ["adb", "shell", "input", "swipe",
         str(sx), str(sy), str(ex), str(ey), str(duration_ms)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": f"Swiped from ({start_x},{start_y}) to ({end_x},{end_y})"}


def type_text(text: str, purpose: str = "") -> dict:
    """Type text on the device. The text input field must already be focused.

    Supports all characters including Chinese/Unicode via ADBKeyboard.
    Falls back to `adb shell input text` for ASCII-only text when ADBKeyboard
    is not installed or not set as the active IME.

    Args:
        text: The text string to type.
        purpose: Why are you typing this text?

    Returns:
        dict with status and message.
    """
    if not text:
        return {"status": "success", "message": "Ignored empty text"}

    short = text[:30] + ("…" if len(text) > 30 else "")

    # Check if ADBKeyboard is the active IME.
    ime_result = subprocess.run(
        ["adb", "shell", "settings", "get", "secure", "default_input_method"],
        capture_output=True,
        text=True,
    )
    adbkeyboard_active = "adbkeyboard" in ime_result.stdout.strip().lower()

    if adbkeyboard_active:
        # ADBKeyboard broadcast using base64 encoding.
        # ADB_INPUT_B64 is the recommended method for modern Android (Oreo+):
        # raw UTF-8 in am broadcast arguments is silently dropped on Oreo and later.
        # base64 encoding avoids all shell quoting and encoding issues.
        # Note: am broadcast for non-ordered broadcasts always outputs result=0,
        # so we rely on IME detection above rather than parsing broadcast output.
        b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
        result = subprocess.run(
            ["adb", "shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", b64],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return {"status": "success", "message": f"Typed via ADBKeyboard: {short}"}
        return {"status": "error", "error_message": f"ADBKeyboard broadcast failed: {result.stderr}"}

    # Fallback: adb shell input text (ASCII / Latin only).
    # `input text` crashes (NPE) on chars KeyCharacterMap cannot map (Chinese, emoji…).
    # Escape in order: % → %% (literal percent), space → %s, newline → %n, then ' for shell.
    safe_text = (
        text
        .replace("%", "%%")
        .replace(" ", "%s")
        .replace("\n", "%n")
        .replace("'", "'\\''")
    )
    result = subprocess.run(
        ["adb", "shell", f"input text '{safe_text}'"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": f"Typed via input text: {short}"}


def press_keycode(keycode: str, purpose: str = "") -> dict:
    """Send a key event to the device by keycode.

    Common keycodes: KEYCODE_BACK (4), KEYCODE_HOME (3), KEYCODE_ENTER (66),
    KEYCODE_DEL (67), KEYCODE_TAB (61), KEYCODE_DPAD_UP (19), KEYCODE_DPAD_DOWN (20),
    KEYCODE_VOLUME_UP (24), KEYCODE_VOLUME_DOWN (25), KEYCODE_APP_SWITCH (187).

    Args:
        keycode: Android keycode name or number string.
        purpose: Why are you pressing this key?

    Returns:
        dict with status and message.
    """
    result = subprocess.run(
        ["adb", "shell", "input", "keyevent", str(keycode)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": f"Pressed keycode: {keycode}"}


def wait(seconds: float = 2.0, purpose: str = "") -> dict:
    """Wait for a specified duration. Use this to wait for UI animations or loading.

    Args:
        seconds: Number of seconds to wait. Default 2.0.
        purpose: What are you waiting for?

    Returns:
        dict with status and message.
    """
    time.sleep(seconds)
    return {"status": "success", "message": f"Waited {seconds} seconds"}


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
    """Get the current screen resolution of the connected Android device (accounts for rotation).

    Returns:
        dict: {"width": int, "height": int} representing the screen dimensions in pixels.
    """
    try:
        w, h = _get_screen_dimensions()
        return {"width": w, "height": h}
    except Exception as e:
        return {"status": "error", "error_message": f"Failed to get screen size: {e}"}


def resize_screenshot(png_bytes: bytes, max_size: int = 640) -> bytes:
    """Resize a screenshot to reduce token usage when sending to LLM.

    Preserves aspect ratio, scales the long edge to max_size pixels,
    pads the image to a 1:1 aspect ratio with a white background (placed at top-left),
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
    else:
        new_w, new_h = w, h

    # Convert to RGB (JPEG doesn't support alpha)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Pad to 1:1 ratio with white background, image centered
    max_dim = max(new_w, new_h)
    padded_img = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
    offset_x = (max_dim - new_w) // 2
    offset_y = (max_dim - new_h) // 2
    padded_img.paste(img, (offset_x, offset_y))

    buf = io.BytesIO()
    padded_img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def push_file(local_path: str, remote_path: str) -> dict:
    """Upload a file from the host computer to the Android device.

    Args:
        local_path: Path to the file on the host computer.
        remote_path: Destination path on the device, e.g. '/sdcard/Download/photo.jpg'.

    Returns:
        dict with status and message.
    """
    result = subprocess.run(
        ["adb", "push", local_path, remote_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": f"Pushed {local_path} -> {remote_path}", "output": result.stdout.strip()}


def pull_file(remote_path: str, local_path: str) -> dict:
    """Download a file from the Android device to the host computer.

    Args:
        remote_path: Path to the device file, e.g. '/sdcard/DCIM/photo.jpg'.
        local_path: Destination path on the host computer.

    Returns:
        dict with status and message.
    """
    result = subprocess.run(
        ["adb", "pull", remote_path, local_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": f"Pulled {remote_path} -> {local_path}", "output": result.stdout.strip()}
