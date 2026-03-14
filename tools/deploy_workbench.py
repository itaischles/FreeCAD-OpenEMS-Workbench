from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "freecad" / "OpenEMSWorkbench"
TARGET_DIR = Path.home() / "AppData" / "Roaming" / "FreeCAD" / "Mod" / "OpenEMSWorkbench"


def deploy() -> Path:
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Workbench source directory not found: {SOURCE_DIR}")

    TARGET_DIR.parent.mkdir(parents=True, exist_ok=True)
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    shutil.copytree(SOURCE_DIR, TARGET_DIR)
    return TARGET_DIR


def main() -> int:
    target = deploy()
    print(f"Deployed OpenEMSWorkbench to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())