from __future__ import annotations

from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resources_dir() -> Path:
    return package_root() / "resources"


def icon_path(name: str) -> str:
    return str(resources_dir() / "icons" / name)
