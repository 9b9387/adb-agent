"""Interaction tools for controlling the Android device via ADB.

All coordinate parameters (x, y) use Gemini's 0-1000 normalized coordinate
system. Internally, they are converted to real screen pixels via:
    real_x = norm_x * screen_width / 1000
"""

import subprocess
import time

# Cache for screen dimensions
_screen_width: int | None = None
_screen_height: int | None = None


def _get_screen_dimensions() -> tuple[int, int]:
    """Get and cache screen dimensions."""
    global _screen_width, _screen_height
    if _screen_width is not None and _screen_height is not None:
        return _screen_width, _screen_height

    result = subprocess.run(
        ["adb", "shell", "wm", "size"],
        capture_output=True,
        text=True,
    )
    for line in result.stdout.strip().splitlines():
        if "Physical size" in line or "Override size" in line:
            size_str = line.split(":")[-1].strip()
            w, h = size_str.split("x")
            _screen_width, _screen_height = int(w), int(h)
            return _screen_width, _screen_height

    raise RuntimeError(f"Could not parse screen size: {result.stdout}")


def _to_real_coords(norm_x: int, norm_y: int) -> tuple[int, int]:
    """Convert 0-1000 normalized coordinates to real screen pixels."""
    w, h = _get_screen_dimensions()
    real_x = int(norm_x * w / 1000)
    real_y = int(norm_y * h / 1000)
    return real_x, real_y


def adb_shell(command: str) -> dict:
    """Execute an arbitrary ADB shell command on the device.

    Use this for actions not covered by other tools: launching/stopping apps,
    opening URLs, querying device state, managing files, etc.
    Example: adb_shell('am start -a android.intent.action.VIEW -d https://google.com')

    Args:
        command: Shell command string to run on the device.

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


def tap(x: int, y: int) -> dict:
    """Tap a point on the screen.

    Args:
        x: Horizontal coordinate in 0-1000 range (0=left, 1000=right).
        y: Vertical coordinate in 0-1000 range (0=top, 1000=bottom).

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


def long_press(x: int, y: int, duration_ms: int = 1000) -> dict:
    """Long press a point on the screen.

    Args:
        x: Horizontal coordinate in 0-1000 range.
        y: Vertical coordinate in 0-1000 range.
        duration_ms: Press duration in milliseconds. Default 1000ms.

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


def double_tap(x: int, y: int) -> dict:
    """Double tap a point on the screen.

    Args:
        x: Horizontal coordinate in 0-1000 range.
        y: Vertical coordinate in 0-1000 range.

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


def swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> dict:
    """Swipe from one point to another on the screen.

    Args:
        start_x: Start horizontal coordinate in 0-1000 range.
        start_y: Start vertical coordinate in 0-1000 range.
        end_x: End horizontal coordinate in 0-1000 range.
        end_y: End vertical coordinate in 0-1000 range.
        duration_ms: Swipe duration in milliseconds. Default 300ms.

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


def type_text(text: str) -> dict:
    """Type text on the device. The text input field must already be focused.

    Special characters and spaces are handled automatically.

    Args:
        text: The text string to type.

    Returns:
        dict with status and message.
    """
    if not text:
        return {"status": "success", "message": "Ignored empty text"}

    # Android's `input text` officially expects spaces to be '%s'
    safe_text = text.replace(" ", "%s")
    
    # Escape single quotes for shell safety: ' -> '\''
    safe_text = safe_text.replace("'", "'\\''")

    # Pass the entire parsed command as one string to `adb shell`
    # so Android's /system/bin/sh processes the wrapping single quotes
    result = subprocess.run(
        ["adb", "shell", f"input text '{safe_text}'"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}"}


def press_keycode(keycode: str) -> dict:
    """Send a key event to the device by keycode.

    Common keycodes: KEYCODE_BACK (4), KEYCODE_HOME (3), KEYCODE_ENTER (66),
    KEYCODE_DEL (67), KEYCODE_TAB (61), KEYCODE_DPAD_UP (19), KEYCODE_DPAD_DOWN (20),
    KEYCODE_VOLUME_UP (24), KEYCODE_VOLUME_DOWN (25), KEYCODE_APP_SWITCH (187).

    Args:
        keycode: Android keycode name or number string.

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


def wait(seconds: float = 2.0) -> dict:
    """Wait for a specified duration. Use this to wait for UI animations or loading.

    Args:
        seconds: Number of seconds to wait. Default 2.0.

    Returns:
        dict with status and message.
    """
    time.sleep(seconds)
    return {"status": "success", "message": f"Waited {seconds} seconds"}


