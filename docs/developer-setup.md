# Developer Setup

## Runtime model

FreeCAD workbenches run inside FreeCAD's embedded Python environment, not inside the repository virtual environment.

Use the repository virtual environment only for pure-Python tooling such as unit tests, formatting, or helper scripts. Validate workbench loading inside FreeCAD itself.

## Deployment

Run the deployment helper:

```powershell
python tools/deploy_workbench.py
```

This creates `%APPDATA%\\FreeCAD\\Mod` if needed and mirrors `freecad/OpenEMSWorkbench` into `%APPDATA%\\FreeCAD\\Mod\\OpenEMSWorkbench`.

## Phase 1 manual verification

1. Deploy the workbench.
2. Start FreeCAD 1.0.
3. Confirm `OpenEMS` appears in the workbench selector.
4. Switch to the workbench and confirm the placeholder toolbar command is visible.
5. Trigger the placeholder command and confirm a message appears in the FreeCAD report view.
