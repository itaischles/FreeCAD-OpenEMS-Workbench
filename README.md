# FreeCAD-openEMS-workbench
A FreeCAD workbench for building openEMS electromagnetic simulation models directly within FreeCAD.

## Status: Work In Progress
This project is still under active development.

What this means:
- Core workflow pieces are already in place and tested.
- Some important simulation features are still being completed.
- UI details, data model details, and exporter behavior may still change before the first MVP is finalized.

## What This Workbench Does
The goal is to make a practical in-FreeCAD simulation workflow:
- Prepare geometry in FreeCAD.
- Define an OpenEMS analysis setup.
- Assign materials, domain, boundaries, and mesh.
- Export a runnable openEMS Python model.
- Run simulation with runtime checks and preflight validation.
