"""ADK Web wrapper for the real browser_agent package."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "browser_agent"
PACKAGE_ALIAS = "adk_web_real_browser_agent"


def _load_package_alias():
    if PACKAGE_ALIAS in sys.modules:
        return sys.modules[PACKAGE_ALIAS]

    spec = importlib.util.spec_from_file_location(
        PACKAGE_ALIAS,
        PACKAGE_ROOT / "__init__.py",
        submodule_search_locations=[str(PACKAGE_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create import spec for browser_agent.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_ALIAS] = module
    spec.loader.exec_module(module)
    return module


_load_package_alias()
root_agent = importlib.import_module(f"{PACKAGE_ALIAS}.agent").root_agent
