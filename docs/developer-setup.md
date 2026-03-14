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

## Phase 4 manual verification

1. Deploy the workbench and open FreeCAD with a new document.
2. Click `Create Analysis` and verify an `openEMS Analysis` object appears.
3. Create one Simulation, one Grid, one Boundary, at least one Material, and one Port.
4. Select the Analysis object and run `Set Active Analysis`.
5. Select all created OpenEMS objects and run `Assign Selected To Active Analysis`.
6. Select `Run Preflight` and verify report-view output ends with a summary line.
7. Intentionally break the setup (for example remove the Grid from analysis group or duplicate a port number) and run preflight again.
8. Verify preflight prints actionable error lines and reports failure when errors are present.
9. Save, close, and reopen the document; verify analysis group membership and object properties are preserved.
