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

## Phase 2 manual verification

1. Deploy the workbench.
2. Start FreeCAD and switch to `OpenEMS` workbench.
3. Create a new FreeCAD document.
4. Use the OpenEMS toolbar to create:
	- Simulation
	- Material
	- Boundary
	- Port
	- Grid
	- DumpBox
5. Confirm each object appears in the tree and exposes properties in the Property editor.
6. Save the document, close FreeCAD, reopen the document, and verify no proxy/view-provider errors appear in Report view.

## Phase 3 manual verification

1. Deploy the workbench.
2. Start FreeCAD and switch to `OpenEMS` workbench.
3. Create one object of each type (Simulation, Material, Boundary, Port, Grid, DumpBox).
4. Select one OpenEMS object and trigger `Edit Selected OpenEMS Object` from the toolbar/menu.
5. Change one value in the task panel and click `OK`; verify the property updates in the Property editor.
6. Re-open edit mode and click `Cancel`; verify no additional changes are applied.
7. Double-click each OpenEMS object in the tree and verify the corresponding task panel opens.
8. Save the document, close FreeCAD, reopen it, and verify edited values are preserved without report-view errors.
