"""Security helpers for browser-agent trust boundaries."""

from __future__ import annotations

import re
from pathlib import Path

LOCAL_PATH_PATTERN = re.compile(
    r"""(?P<path>(?:~|/)[^\s"'`，。！？；：、）】》〉」』]+)"""
)


def normalize_local_path(raw_path: str) -> str:
    """Normalize a local path for authorization checks."""
    return str(Path(raw_path).expanduser().resolve(strict=False))


def extract_explicit_local_paths(text: str | None) -> list[str]:
    """Extract explicit local file paths that the user mentioned in text."""
    if not text:
        return []

    normalized_paths = {
        normalize_local_path(match.group("path"))
        for match in LOCAL_PATH_PATTERN.finditer(text)
    }
    return sorted(normalized_paths)


def is_explicitly_authorized_path(file_path: str, allowed_paths: list[str]) -> bool:
    """Return whether a file path was explicitly authorized by the user task."""
    if not allowed_paths:
        return False
    return normalize_local_path(file_path) in {
        normalize_local_path(path) for path in allowed_paths
    }
