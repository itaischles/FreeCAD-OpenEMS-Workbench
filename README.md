# FreeCAD OpenEMS Workbench

This repository hosts a custom FreeCAD workbench for building and exporting openEMS FDTD simulations.

Phase 1 establishes the external workbench scaffold, FreeCAD entrypoints, a placeholder command path, and a deployment helper for loading the workbench from the user FreeCAD profile.

## Repository layout

- `freecad/OpenEMSWorkbench/` contains the workbench package that FreeCAD loads from its `Mod` directory.
- `tools/deploy_workbench.py` copies the workbench package into `%APPDATA%\\FreeCAD\\Mod\\OpenEMSWorkbench`.
- `tests/unit/` contains import-level smoke tests that can run outside FreeCAD.

## Development workflow

1. Keep the source of truth in this repository.
2. Run `tools/deploy_workbench.py` to mirror the workbench into the user FreeCAD `Mod` directory.
3. Start FreeCAD and switch to the `OpenEMS` workbench.

Git usage conventions for this repository are documented in `docs/git-workflow.md`.

End-user OpenEMS install and FreeCAD linkage steps are documented in `docs/user-openems-setup.md`.

The local virtual environment helper in `SetupBasicPythonEnv.bat` is optional and not part of the workbench runtime contract.
