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
    logs_dir = root / "logs"
    run_dir = root / "run"
    script_path = root / "openems_export.py"
    return {
        "root": root,
        "stl_dir": stl_dir,
        "logs_dir": logs_dir,
        "run_dir": run_dir,
        "stdout_log": logs_dir / "stdout.log",
        "stderr_log": logs_dir / "stderr.log",
        "script": script_path,
    }


def ensure_export_dirs(paths: dict[str, Path]) -> None:
    paths["root"].mkdir(parents=True, exist_ok=True)
    paths["stl_dir"].mkdir(parents=True, exist_ok=True)
    paths["logs_dir"].mkdir(parents=True, exist_ok=True)
    paths["run_dir"].mkdir(parents=True, exist_ok=True)
