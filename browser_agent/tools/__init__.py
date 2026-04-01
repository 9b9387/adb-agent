"""Aggregated tool list for the browser automation agent."""

from agent_shared.memo import read_memo
from agent_shared.memo import write_memo
from agent_shared.planning import advance_plan

from .browser import click
from .browser import close_browser
from .browser import launch_browser
from .browser import open_url
from .browser import press_key
from .browser import read_page
from .browser import scroll
from .browser import set_file_input
from .browser import type_text
from .browser import wait_for

ALL_TOOLS = [
    advance_plan,
    launch_browser,
    open_url,
    click,
    type_text,
    set_file_input,
    press_key,
    scroll,
    wait_for,
    read_page,
    close_browser,
    write_memo,
    read_memo,
]
