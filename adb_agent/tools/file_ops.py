"""File transfer operations between host and Android device via ADB."""

import subprocess


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
        remote_path: Path to the file on the device, e.g. '/sdcard/DCIM/photo.jpg'.
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



