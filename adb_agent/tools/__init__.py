"""Aggregated list of all ADB tool functions for the agent."""

from .actions import (
    clear_app_data,
    close_app,
    double_tap,
    finish_task,
    get_clipboard,
    long_press,
    open_app,
    open_url,
    press_back,
    press_enter,
    press_home,
    press_key,
    press_recent_apps,
    set_clipboard,
    swipe,
    tap,
    type_text,
    wait,
)
from .device_info import (
    get_battery_info,
    get_current_app,
    get_device_info,
    get_installed_packages,
    get_screen_state,
    lock_screen,
    wake_screen,
)
from .file_ops import (
    delete_file,
    list_files,
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
    tap,
    long_press,
    double_tap,
    swipe,
    type_text,
    set_clipboard,
    get_clipboard,
    press_key,
    press_back,
    press_home,
    press_enter,
    press_recent_apps,
    open_app,
    close_app,
    clear_app_data,
    open_url,
    wait,
    finish_task,
    # File operations
    push_file,
    pull_file,
    list_files,
    delete_file,
    # Device info
    get_device_info,
    get_battery_info,
    get_current_app,
    get_installed_packages,
    get_screen_state,
    wake_screen,
    lock_screen,
]
