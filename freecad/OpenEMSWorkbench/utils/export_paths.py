from __future__ import annotations

from pathlib import Path
import re


def _sanitize(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return text.strip("_") or "unnamed"


def build_export_paths(base_dir: str | Path, document_name: str, analysis_name: str) -> dict[str, Path]:
    base = Path(base_dir)
    root = base / _sanitize(document_name) / _sanitize(analysis_name)
    stl_dir = root / "stl"
    script_path = root / "openems_export.py"
    return {
        "root": root,
        "stl_dir": stl_dir,
        "script": script_path,
    }


def ensure_export_dirs(paths: dict[str, Path]) -> None:
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["stl_dir"].mkdir(parents=True, exist_ok=True)
