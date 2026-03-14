# OpenEMS Setup Guide for FreeCAD Users

This guide is for users who want to run simulations from the OpenEMS FreeCAD workbench with minimal technical setup.

## Goal

After this setup, you should be able to:

1. Open FreeCAD and switch to the OpenEMS workbench.
2. Configure runtime once.
3. Run Validate Runtime successfully.
4. Run Simulation from the workbench.

## 1) Install openEMS locally

Install openEMS on Windows so that the main executable exists at a known location (for example `C:\openEMS\openEMS.exe`).

If you already installed openEMS, verify it by running this in PowerShell:

- `C:\openEMS\openEMS.exe --help`

Expected result: version/help text is printed.

## 2) Ensure openEMS Python wheels are available

Most Windows openEMS installs include Python wheels under:

- `C:\openEMS\python`

Check that this folder contains wheel files similar to:

- `openems-...-cp314-...win_amd64.whl`
- `csxcad-...-cp314-...win_amd64.whl`

(Use `cp313` wheels if your Python is 3.13, `cp314` wheels if your Python is 3.14.)

## 3) Install the openEMS Python packages into your chosen Python runtime

Choose the Python runtime you want FreeCAD to use for simulation runs.

Example using this repository virtual environment:

- `python -m pip install C:\openEMS\python\csxcad-0.6.3-cp314-cp314-win_amd64.whl C:\openEMS\python\openems-0.0.36-cp314-cp314-win_amd64.whl`

## 4) Set OPENEMS_INSTALL_DIR once (required for DLL loading)

Run once in PowerShell:

- `setx OPENEMS_INSTALL_DIR "C:\openEMS"`

Then restart FreeCAD (and any terminals used for testing).

## 5) Verify Python runtime manually (optional but recommended)

Run:

- `python -c "import os; os.add_dll_directory(r'C:\openEMS'); import openEMS, CSXCAD; print('OK')"`

Expected result: `OK`.

## 6) Link runtime in FreeCAD workbench

1. Open FreeCAD.
2. Switch to OpenEMS workbench.
3. Run `Configure Runtime...`.
4. Select your Python executable.
5. Run `Validate Runtime`.

Expected result: runtime validation passes.

## 7) Run a test simulation

1. Create a valid analysis (Simulation, Grid, Material, Boundary, Port).
2. Set Simulation to blocking mode.
3. Run `Run Simulation`.
4. Check Report view for script path and stdout/stderr log paths.

## Troubleshooting

### Validate Runtime times out

1. Confirm `OPENEMS_INSTALL_DIR` is set to `C:\openEMS`.
2. Restart FreeCAD after setting environment variables.
3. Confirm selected Python matches the wheel version (cp313 vs cp314).

### No module named openEMS

1. Install the openEMS and csxcad wheel files into the same Python selected in Configure Runtime.
2. Verify with a direct Python import test.

### DLL load failed while importing CSXCAD

1. Confirm `OPENEMS_INSTALL_DIR` points to openEMS root.
2. Confirm that folder contains `openEMS.dll`, `CSXCAD.dll`, and related runtime DLLs.
3. Restart FreeCAD after environment changes.

### openEMS.exe works but Run Simulation fails

This workbench run mode executes a Python script. Use a Python interpreter that can import openEMS and CSXCAD, not openEMS.exe, for SolverExecutable.

## Notes for future UX improvements

The ideal future flow is fully guided onboarding in FreeCAD:

1. Auto-detect openEMS install.
2. Auto-install wheel packages when needed.
3. One-click runtime setup validation.
4. No manual path handling for typical users.
