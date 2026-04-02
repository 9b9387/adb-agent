"""Tools for discovering and loading agent skills.

Scanning order — first directory wins on name collision:
  1. $SKILLS_BASE_DIR   (env var, if set)
  2. .agents/skills/    (project-level, cwd)
  3. .claude/skills/    (project-level, legacy compat, cwd)
  4. ~/.agents/skills/  (user-level)
  5. ~/.claude/skills/  (user-level, legacy compat)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from google.adk.skills import list_skills_in_dir, load_skill_from_dir
from google.adk.skills.models import Frontmatter

_SKILL_FILENAME = "SKILL.md"
_logger = logging.getLogger(__name__)


def _skill_search_dirs() -> list[Path]:
    """Return candidate skill base directories in priority order."""
    dirs: list[Path] = []
    env = os.environ.get("SKILLS_BASE_DIR")
    if env:
        dirs.append(Path(env).expanduser())
    cwd = Path.cwd()
    home = Path.home()
    dirs += [
        cwd / ".agents" / "skills",
        cwd / ".claude" / "skills",
        home / ".agents" / "skills",
        home / ".claude" / "skills",
    ]
    return dirs


def _discover_all_skills() -> tuple[dict[str, tuple[Frontmatter, Path]], list[str]]:
    """Discover skills across all search dirs.

    Returns:
        skills_map: skill name → (Frontmatter, skill_dir)
        warnings:   human-readable messages for invalid / skipped skills
    """
    skills_map: dict[str, tuple[Frontmatter, Path]] = {}
    warnings: list[str] = []

    for base in _skill_search_dirs():
        if not base.is_dir():
            continue

        # ADK's list_skills_in_dir handles parsing and logs its own warnings
        # for skills that fail validation; we collect the valid ones here.
        found: dict[str, Frontmatter] = list_skills_in_dir(base)

        # Walk the dir to surface skills that failed ADK validation as warnings.
        for entry in sorted(base.iterdir()):
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            if not (entry / _SKILL_FILENAME).is_file():
                continue
            name = entry.name
            if name in skills_map:
                # Higher-priority dir already owns this name.
                continue
            if name in found:
                skills_map[name] = (found[name], entry)
            else:
                warnings.append(
                    f"Skill '{name}' at {entry} has invalid SKILL.md"
                    " (check that frontmatter 'name' matches directory name)"
                )

    return skills_map, warnings


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

def list_skills() -> dict:
    """List all available agent skills with their names, descriptions, and locations.

    Returns:
        dict with 'status', 'skills' (list of {name, description, location}),
        'count', and optionally 'warnings' for invalid skills found during scan.
    """
    skills_map, warnings = _discover_all_skills()

    if not skills_map and not warnings:
        searched = [str(d) for d in _skill_search_dirs()]
        return {
            "status": "error",
            "error_message": f"No skills found. Searched directories: {searched}",
        }

    skills = [
        {
            "name": fm.name,
            "description": fm.description,
            "location": str(skill_dir),
        }
        for _, (fm, skill_dir) in sorted(skills_map.items())
    ]

    result: dict = {"status": "success", "skills": skills, "count": len(skills)}
    if warnings:
        result["warnings"] = warnings
    return result


def read_skill(skill_name: str) -> dict:
    """Read the full instructions for a specific agent skill.

    The content is wrapped in a structured <skill_content name="..."> block
    per the agentskills.io activation spec. Any bundled resources (references,
    assets, scripts) are listed separately so the model knows what additional
    material is available without eagerly loading it.

    Args:
        skill_name: Exact skill name as returned by list_skills() or
            search_skills(). Use those tools to discover valid names.

    Returns:
        dict with 'status', 'skill_name', 'content' (wrapped instructions),
        'resources' (dict of available resource names), and 'location'.
    """
    if not skill_name or not skill_name.strip():
        return {"status": "error", "error_message": "skill_name is required."}

    name = skill_name.strip()
    skills_map, _ = _discover_all_skills()

    if name not in skills_map:
        valid_names = sorted(skills_map.keys())
        return {
            "status": "error",
            "error_message": (
                f"Skill '{name}' not found. "
                f"Valid skill names: {valid_names}"
            ),
        }

    _, skill_dir = skills_map[name]
    try:
        skill = load_skill_from_dir(skill_dir)
    except Exception as exc:
        return {"status": "error", "error_message": f"Failed to load skill '{name}': {exc}"}

    # Wrap per agentskills.io activation spec
    wrapped = f'<skill_content name="{skill.name}">\n{skill.instructions}\n</skill_content>'

    resources: dict[str, list[str]] = {}
    if skill.resources.references:
        resources["references"] = skill.resources.list_references()
    if skill.resources.assets:
        resources["assets"] = skill.resources.list_assets()
    if skill.resources.scripts:
        resources["scripts"] = skill.resources.list_scripts()

    return {
        "status": "success",
        "skill_name": skill.name,
        "content": wrapped,
        "resources": resources,
        "location": str(skill_dir),
    }


def search_skills(query: str) -> dict:
    """Search available skills by keyword — matches against names and descriptions.

    Args:
        query: A keyword or phrase to search for (case-insensitive).

    Returns:
        dict with 'status', 'query', 'matches' (list of {name, description,
        location}), and 'count'.
    """
    if not query or not query.strip():
        return {"status": "error", "error_message": "query is required."}

    all_result = list_skills()
    if all_result["status"] != "success":
        return all_result

    needle = query.strip().lower()
    matches = [
        s for s in all_result["skills"]
        if needle in s["name"].lower() or needle in s["description"].lower()
    ]
    return {"status": "success", "query": query, "matches": matches, "count": len(matches)}
