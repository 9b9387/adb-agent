"""Tools for discovering and loading agent skills from the skills base directory."""

from __future__ import annotations

import os
import re
from pathlib import Path

import frontmatter

# Default to ~/.agents/skills; override with SKILLS_BASE_DIR env var.
_DEFAULT_SKILLS_DIR = Path.home() / ".agents" / "skills"
_SKILL_FILENAME = "SKILL.md"


def _skills_base_dir() -> Path:
    env = os.environ.get("SKILLS_BASE_DIR")
    return Path(env).expanduser() if env else _DEFAULT_SKILLS_DIR


def _skill_path(skill_name: str) -> Path | None:
    """Return the SKILL.md path for *skill_name*, or None if not found."""
    base = _skills_base_dir()
    # Support both directory-style skills (skill_name/SKILL.md) and
    # flat-file skills (skill_name or skill_name.md).
    candidates = [
        base / skill_name / _SKILL_FILENAME,
        base / f"{skill_name}.md",
        base / skill_name,  # plain file with no extension
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _extract_description(skill_name: str) -> str:
    """Return the description from a skill's SKILL.md frontmatter, or the first body line."""
    path = _skill_path(skill_name)
    if path is None:
        return "(no description)"
    try:
        post = frontmatter.load(str(path))
        desc = post.get("description", "")
        if desc:
            return re.sub(r"\s+", " ", str(desc)).strip()[:200]
        # Fallback: first non-blank, non-heading line from the Markdown body
        for line in post.content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith(("#", ">", "---")):
                return stripped[:200]
    except Exception:
        pass
    return "(no description)"


def list_skills() -> dict:
    """List all available agent skills with their names and short descriptions.

    Returns:
        dict with 'status' and 'skills' keys. Each skill entry has 'name' and
        'description' fields.
    """
    base = _skills_base_dir()
    if not base.exists():
        return {
            "status": "error",
            "error_message": f"Skills directory not found: {base}",
        }

    skills: list[dict] = []
    seen: set[str] = set()

    for entry in sorted(base.iterdir()):
        if entry.name.startswith("."):
            continue
        # Directory-style skill
        if entry.is_dir():
            skill_md = entry / _SKILL_FILENAME
            if skill_md.is_file():
                name = entry.name
                if name not in seen:
                    seen.add(name)
                    skills.append({"name": name, "description": _extract_description(name)})
        # Flat-file skill (plain file or .md file)
        elif entry.is_file():
            name = entry.stem if entry.suffix == ".md" else entry.name
            if name not in seen:
                seen.add(name)
                skills.append({"name": name, "description": _extract_description(name)})

    return {"status": "success", "skills": skills, "count": len(skills)}


def read_skill(skill_name: str) -> dict:
    """Read the full SKILL.md content for a specific agent skill.

    Args:
        skill_name: The name of the skill to read (e.g. "weather", "browse").

    Returns:
        dict with 'status' and 'content' (the full SKILL.md text), or an error.
    """
    if not skill_name or not skill_name.strip():
        return {"status": "error", "error_message": "skill_name is required."}

    path = _skill_path(skill_name.strip())
    if path is None:
        return {
            "status": "error",
            "error_message": f"Skill '{skill_name}' not found in {_skills_base_dir()}.",
        }

    try:
        content = path.read_text(encoding="utf-8")
        return {
            "status": "success",
            "skill_name": skill_name,
            "content": content,
            "path": str(path),
        }
    except OSError as exc:
        return {"status": "error", "error_message": str(exc)}


def search_skills(query: str) -> dict:
    """Search available skills by keyword — matches against skill names and descriptions.

    Args:
        query: A keyword or phrase to search for (case-insensitive).

    Returns:
        dict with 'status' and 'matches' list, each entry has 'name' and 'description'.
    """
    if not query or not query.strip():
        return {"status": "error", "error_message": "query is required."}

    all_skills_result = list_skills()
    if all_skills_result["status"] != "success":
        return all_skills_result

    needle = query.strip().lower()
    matches = [
        s for s in all_skills_result["skills"]
        if needle in s["name"].lower() or needle in s["description"].lower()
    ]
    return {"status": "success", "query": query, "matches": matches, "count": len(matches)}
