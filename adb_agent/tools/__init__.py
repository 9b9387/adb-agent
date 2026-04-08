"""Aggregated list of all ADB tool functions for the agent."""

from .adb import (
    adb_shell,
    double_tap,
    long_press,
    press_keycode,
    swipe,
    tap,
    type_text,
    wait,
    pull_file,
    push_file,
    get_screen_size,
    check_adb_connection,
)
from .memo import (
    read_memo,
    write_memo,
)
from .planner import (
    update_plan,
    create_plan,
)

ALL_TOOLS = [
    # Planning
    create_plan,
    update_plan,
    # Screen & ADB
    check_adb_connection,
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
    # Session blackboard
    write_memo,
    read_memo,
]
