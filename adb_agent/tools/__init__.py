"""Aggregated list of all ADB tool functions for the agent."""

from .actions import (
    adb_shell,
    double_tap,
    long_press,
    press_keycode,
    swipe,
    tap,
    type_text,
    wait,
)
from .file_ops import (
    pull_file,
    push_file,
)
from .planning import (
    advance_plan,
    create_plan,
)
from .screen import (
    get_screen_size,
)

ALL_TOOLS = [
    # Planning (FIRST — mandatory before actions)
    create_plan,
    advance_plan,
    # Screen
    get_screen_size,
    # Interaction
    adb_shell,
    tap,
    long_press,
    double_tap,
    swipe,
    type_text,
    press_keycode,
    wait,
    # File operations
    push_file,
    pull_file,
]
