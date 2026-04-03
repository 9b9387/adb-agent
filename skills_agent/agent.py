"""Skills agent — discovers, loads, and applies agent skills."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.skills import list_skills_in_dir, load_skill_from_dir
from google.adk.tools.bash_tool import ExecuteBashTool
from google.adk.tools.load_web_page import load_web_page
from google.adk.tools.skill_toolset import SkillToolset
from google.genai import types

load_dotenv()

from .prompts import SYSTEM_INSTRUCTION

_logger = logging.getLogger(__name__)

# Search order: $SKILLS_BASE_DIR > project-level > user-level. First match wins.
_SKILL_BASE_DIRS: list[Path] = [
    *([Path(os.environ["SKILLS_BASE_DIR"]).expanduser()] if os.environ.get("SKILLS_BASE_DIR") else []),
    Path.cwd() / ".agents" / "skills",
    Path.cwd() / ".claude" / "skills",
    Path.home() / ".agents" / "skills",
    Path.home() / ".claude" / "skills",
]


def _build_skill_toolset() -> SkillToolset:
    seen: set[str] = set()
    skills = []
    for base in _SKILL_BASE_DIRS:
        if not base.is_dir():
            continue
        for name in list_skills_in_dir(base):
            if name not in seen:
                seen.add(name)
                try:
                    skills.append(load_skill_from_dir(base / name))
                except Exception as exc:
                    _logger.warning("Skipping skill '%s': %s", name, exc)
    return SkillToolset(skills=skills)


model_name = os.getenv("MODEL_NAME", "gemini-3-flash-preview")

root_agent = Agent(
    name="skills_agent",
    model=model_name,
    description=(
        "An agent that discovers, loads, and applies agent skills (SKILL.md files) "
        "to help users accomplish domain-specific tasks."
    ),
    instruction=SYSTEM_INSTRUCTION,
    tools=[_build_skill_toolset(), load_web_page, ExecuteBashTool()],
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
)
