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

## Phase 5 manual verification

1. Deploy the workbench and open FreeCAD.
2. Build a valid analysis with simulation/grid/material/boundary/port and run preflight to confirm pass.
3. Add one simple `Part::Box` object to the analysis group and one non-box/cylinder shape.
4. Run `Export Dry-Run Script`.
5. Verify report view prints export stats and paths for script + STL directory.
6. Open the generated script and confirm geometry comments include both direct primitive mapping and STL fallback entries.
7. Run export again without changes and verify output file naming/order remains stable.

## Phase 6 manual verification

1. Deploy the workbench and open FreeCAD.
2. Create an analysis and assign one Grid object to it.
3. Run `Show/Hide Mesh Overlay` and verify mesh lines appear in the active 3D view.
4. Run `Show/Hide Mesh Overlay` again and verify the overlay is removed cleanly.
5. Change Grid values such as `BaseResolution`, `MaxResolution`, or `CoordinateSystem`.
6. Run `Refresh Mesh Overlay` and verify the displayed mesh updates.
7. Run `Refresh Mesh Overlay` again without property changes and verify report view indicates refresh skip or no unnecessary redraw behavior.
8. Switch documents or views and verify no stale overlay artifacts remain and no report-view errors occur.

## Phase 7 manual verification

1. Deploy the workbench and open FreeCAD.
2. Create a valid analysis containing Simulation, Grid, Material, Boundary, and Port objects.
3. Run `Configure Runtime...` once and select a Python interpreter that has `openEMS` and `CSXCAD` Python modules.
4. Open Simulation task panel and confirm `RunBlocking` is enabled.
5. Run `Validate Runtime` and verify either:
	- auto-detection finds a compatible Python runtime and reports success, or
	- a clear failure message explains why runtime discovery failed.
6. Run `Run Preflight` and verify warnings/errors are understandable.
7. Run `Run Simulation` and verify report view shows runtime check status, run start, completion/failure, script path, and stdout/stderr log paths.
8. Open the generated `stdout.log` and `stderr.log` files and verify process output was captured.
9. Intentionally set `SolverExecutable` to `openEMS.exe` and rerun `Validate Runtime`; verify it reports script-mode mismatch with actionable guidance.
10. Confirm `Export Dry-Run Script` and mesh overlay commands still behave as expected after run integration.
