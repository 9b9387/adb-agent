"""Device information and state management tools via ADB."""

import subprocess


def get_device_info() -> dict:
    """Get comprehensive device information including name, model, Android version, and serial number.

    Returns:
        dict with device details.
    """
    props = {
        "device_name": "ro.product.device",
        "model": "ro.product.model",
        "brand": "ro.product.brand",
        "android_version": "ro.build.version.release",
        "sdk_version": "ro.build.version.sdk",
        "serial": "ro.serialno",
    }
    info = {}
    for key, prop in props.items():
        result = subprocess.run(
            ["adb", "shell", "getprop", prop],
            capture_output=True,
            text=True,
        )
        info[key] = result.stdout.strip()

    # Also get screen resolution
    result = subprocess.run(
        ["adb", "shell", "wm", "size"],
        capture_output=True,
        text=True,
    )
    info["screen_resolution"] = result.stdout.strip()

    return {"status": "success", **info}


def get_battery_info() -> dict:
    """Get battery status including level, charging state, and temperature.

    Returns:
        dict with battery details.
    """
    result = subprocess.run(
        ["adb", "shell", "dumpsys", "battery"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}

    info = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            info[key] = value.strip()

    return {"status": "success", **info}


def get_current_app() -> dict:
    """Get the currently focused app's package name and activity.

    Returns:
        dict with current foreground app information.
    """
    result = subprocess.run(
        ["adb", "shell", "dumpsys", "window", "displays"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}

    for line in result.stdout.splitlines():
        if "mCurrentFocus" in line or "mFocusedApp" in line:
            return {"status": "success", "current_app": line.strip()}

    return {"status": "success", "current_app": "Could not determine", "raw": result.stdout[:500]}


def get_installed_packages(filter_keyword: str = "") -> dict:
    """List installed packages on the device, optionally filtered by keyword.

    Args:
        filter_keyword: Optional keyword to filter package names. If empty, returns all packages.

    Returns:
        dict with list of package names.
    """
    result = subprocess.run(
        ["adb", "shell", "pm", "list", "packages"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}

    packages = []
    for line in result.stdout.splitlines():
        pkg = line.replace("package:", "").strip()
        if pkg and (not filter_keyword or filter_keyword.lower() in pkg.lower()):
            packages.append(pkg)

    return {"status": "success", "count": len(packages), "packages": packages}


def get_screen_state() -> dict:
    """Check if the screen is on and whether the device is locked.

    Returns:
        dict with screen_on (bool) and locked (bool) status.
    """
    result = subprocess.run(
        ["adb", "shell", "dumpsys", "power"],
        capture_output=True,
        text=True,
    )
    output = result.stdout
    screen_on = "mWakefulness=Awake" in output or "Display Power: state=ON" in output
    locked = "mUserActivitySummary=0" in output

    result2 = subprocess.run(
        ["adb", "shell", "dumpsys", "window", "policy"],
        capture_output=True,
        text=True,
    )
    is_locked = "isStatusBarKeyguard=true" in result2.stdout or "mShowingLockscreen=true" in result2.stdout

    return {"status": "success", "screen_on": screen_on, "locked": is_locked}


def wake_screen() -> dict:
    """Wake up the device screen if it is off.

    Returns:
        dict with status and message.
    """
    result = subprocess.run(
        ["adb", "shell", "input", "keyevent", "224"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": "Screen wakeup signal sent"}


def lock_screen() -> dict:
    """Lock the device screen (put it to sleep).

    Returns:
        dict with status and message.
    """
    result = subprocess.run(
        ["adb", "shell", "input", "keyevent", "223"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"status": "error", "error_message": result.stderr}
    return {"status": "success", "message": "Screen lock signal sent"}
