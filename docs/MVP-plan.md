# MVP plan for the FreeCAD OpenEMS workbench

## Goal

Create a practical first version of the workbench that supports a real simulation workflow inside FreeCAD.

The first target is not to build every long-term feature at once. The first target is to make the workbench reliably do the full basic job:

- Create geometry in FreeCAD.
- Create an OpenEMS analysis.
- Assign materials to the geometry.
- Define the simulation box, boundary conditions, and mesh.
- Export a real openEMS model.
- Run the simulation.
- Save results to a user-defined folder.

After that, the next target is to add the missing features needed for the coaxial-cable workflow:

- Waveguide port support.
- Sinusoidal excitation support.
- Field dump output that can later be viewed inside FreeCAD.

Long term, I want to view simulation results inside FreeCAD, but this is not part of the first MVP.

## Main idea

The project already has a good workbench structure:

- Analysis objects exist.
- Task panels exist.
- Preflight checks exist.
- Export exists.
- Solver execution exists.
- Mesh overlay exists.

The main missing work is that some important simulation features are still only partial or placeholders. The plan should therefore focus first on turning the current scaffold into a real usable simulation pipeline.

Two cross-cutting requirements should be included early in the implementation:

- Automatic preflight when the user clicks Run Simulation, so setup mistakes are caught before launching the solver.
- Reliable unit handling, so FreeCAD geometry units are converted and passed to openEMS consistently.

## Recommended implementation order

### Phase 1: align documentation with the real project

Update the project documentation so it reflects the current state of the repository and the real MVP target.

This phase should:

- Update stale phase descriptions.
- Describe what is already implemented.
- Describe what is still missing.
- Describe the first practical MVP target clearly.

Reason:

The repository already went beyond the very early scaffold stage, so the written plan should match reality before more features are added.

Commit-sized tasks:

1. Commit 1.1: Update README and docs intro text so phase status matches current repository reality.
2. Commit 1.2: Add a short MVP scope summary that clearly states what is in scope and out of scope.
3. Commit 1.3: Add one simple workflow section that describes the user path from model setup to simulation run.

### Phase 2: add material assignment to geometry

Materials already exist as objects, but the workbench still needs a real assignment model that matches openEMS usage.

In openEMS, material definitions and geometry are separate:

- You create a named property (for example PEC metal or dielectric material).
- You assign geometry primitives to that property.
- Overlap is resolved by primitive priority.

This phase adds the FreeCAD-side assignment workflow and data, but does not yet generate final openEMS script commands.

This phase should:

- Let the user assign exactly one material to each analysis geometry object.
- Keep Phase 2 material scope simple: PEC metal or dielectric/general material.
- Store assignments in a stable way in the FreeCAD document.
- Restore assignments correctly after saving and reopening.
- Carry assignment and priority metadata forward for Phase 3 export.

Recommended simple workflow:

- The user selects one or more geometry objects in the analysis.
- The user opens or creates a material object.
- The user assigns the current selection to that material.
- The user can unassign or reassign geometry as needed.
- The material panel shows which geometry is currently assigned.

Reason:

Without this step, export cannot know which geometry is PEC metal and which geometry is dielectric. openEMS expects geometry to be attached to named properties, so assignment must be explicit before real export can work.

Commit-sized tasks:

1. Commit 2.1: Add persistent geometry-link assignment properties on material objects, including metadata needed for export handoff.
2. Commit 2.2: Add task panel controls to assign selected geometry, unassign geometry, and list assigned geometry for a material.
3. Commit 2.3: Add preflight checks so each analysis geometry has exactly one material assignment, with no stale links and no duplicate assignments across materials.
4. Commit 2.4: Add tests for assign/reassign/unassign flows and save/reopen persistence.
5. Commit 2.5: Add a documented handoff contract from Phase 2 to Phase 3 for geometry-to-material mapping and priority usage.

Out of scope for this phase:

- Advanced openEMS material options (for example sigma, anisotropy vectors, and spatial weighting functions).
- Final CSX/openEMS command emission (implemented in Phase 3).

### Phase 3: export real geometry and materials

The exporter currently reads many things correctly, but large parts of the generated script are still comments instead of real CSX/openEMS commands.

This phase should:

- Export boxes and cylinders as real simulation objects.
- Connect exported geometry to the assigned material.
- Keep STL fallback for shapes that cannot yet be exported directly.
- Produce a script that is physically meaningful, not just structurally correct.

Reason:

This is the most important technical gap between the current scaffold and a usable simulation workbench.

Commit-sized tasks:

1. Commit 3.1: Extend document reader model to carry geometry-material assignment data into export.
2. Commit 3.2: Generate real CSX geometry for directly supported primitives.
3. Commit 3.3: Generate real material definitions and bind primitives to those materials.
4. Commit 3.4: Keep STL fallback path and add tests that cover both direct and fallback export.

### Phase 4: Configure simulation bounding box and units

The simulation space should be built automatically from the geometry included in the analysis, with consistent unit conversion from FreeCAD to openEMS. The bounding box will be displayed in FreeCAD as a box with configurable dimensions, but by default will include the simulation geometry with no margins. Boundary conditions will be assigned to this boundary box by means of clicking on a face and selecting the appropriate boundary condition. The boundary conditions will then be exported to the python script for the openEMS simulation using the exporter.

This phase should:

- Compute the bounding box of the full geometry in the analysis.
- Show this simulation box in FreeCAD as an editable object with configurable dimensions.
- Default to no margin so the box initially matches the included simulation geometry.
- Let the user assign boundary conditions by selecting a box face and choosing a boundary type.
- Export the selected face boundary conditions into the generated openEMS Python script.
- Define one clear unit-conversion path from FreeCAD units to openEMS units and apply it everywhere in export and run.
- End with one unified model: simulation box + per-face boundaries in the same object, with legacy separate boundary/simulation-box objects and data model removed.

Reason:

This matches the intended workflow: users can see and edit the simulation region directly in FreeCAD, assign boundaries interactively, and trust that the exported script reflects exactly what they configured. It also removes legacy duplication so there is only one source of truth for simulation-region and boundary data.

Commit-sized tasks:

1. Commit 4.1: Compute the analysis geometry bounding box and create/update a visible simulation-box object that defaults to tight fit (no margin).
2. Commit 4.2: Add simulation-box editing support in FreeCAD so dimensions can be adjusted when needed.
3. Commit 4.3: Implement face-based boundary assignment workflow on the simulation box and store per-face boundary settings persistently.
4. Commit 4.4: Export per-face boundary settings from the simulation box into real openEMS boundary commands in the generated Python script.
5. Commit 4.5: Enforce one explicit unit contract so the units shown in FreeCAD are the exact same units openEMS reads from the exported Python input (no hidden scale mismatch), and apply this consistently in geometry, boundary coordinates, exporter, and run pipeline.
6. Commit 4.6: Migrate legacy boundary/simulation-box data to the new unified simulation-box object model, then remove legacy separate boundary/simulation-box objects, UI paths, and exporter/preflight dependencies.

### Phase 5: connect mesh to the real model extent

The mesh overlay already exists, but it should be tied to the real simulation domain rather than a generic symmetric grid.

This phase should:

- Use the automatically computed simulation box.
- Generate mesh lines based on that region.
- Keep the result deterministic so tests stay stable.
- Update correctly when geometry changes.
- Remove the legacy generic symmetric mesh-domain path once simulation-box-driven meshing is stable.

Reason:

The mesh should correspond to the actual simulation model, especially for practical work such as cables and waveguides.

Commit-sized tasks:

1. Commit 5.1: Drive mesh domain from computed simulation box instead of generic symmetric extents.
2. Commit 5.2: Update mesh overlay refresh logic so geometry changes trigger correct mesh updates.
3. Commit 5.3: Add deterministic mesh generation tests for repeated export and overlay refresh.
4. Commit 5.4: Remove legacy symmetric mesh-domain code paths and related UI/validation assumptions after migration.

### Phase 6: make dump boxes generate real field output

DumpBox objects already exist, but they are still mostly placeholders in the exported script.

This phase should:

- Export real field-dump definitions.
- Save the dump results into the chosen results folder.
- Support at least the electric field first.
- Remove placeholder dumpbox export behavior once real dump commands are implemented.

Reason:

This is the shortest path toward later visualization inside FreeCAD.

Commit-sized tasks:

1. Commit 6.1: Extend dumpbox export model with explicit dump type and frequency handling.
2. Commit 6.2: Generate real openEMS field-dump commands for at least electric-field outputs.
3. Commit 6.3: Ensure dump output paths are created under the user-defined results folder.
4. Commit 6.4: Add tests that verify dump commands and output path generation.
5. Commit 6.5: Remove legacy placeholder dumpbox script stubs and temporary compatibility branches.

### Phase 7: stabilize one simple end-to-end runnable case

Before adding the more advanced coax-specific features, build one simpler case that is known to work from start to finish.

This phase should:

- Use the currently supported simple excitation path.
- Run preflight automatically before every simulation run.
- Pass preflight cleanly.
- Export a real script.
- Run successfully.
- Produce output files and logs.

Reason:

This creates a reliable base and reduces debugging when more advanced features are added.

Commit-sized tasks:

1. Commit 7.1: Enforce automatic preflight invocation before simulation run command executes.
2. Commit 7.2: Improve run-time reporting so preflight failures are shown clearly and block solver launch.
3. Commit 7.3: Add one stable minimal example that passes preflight, exports, and runs end to end.
4. Commit 7.4: Add execution tests covering auto-preflight and run gating behavior.

### Phase 8: add waveguide port support

Waveguide ports are one of the most important missing features for the intended coaxial-cable workflow.

This phase should:

- Extend the port object with the needed waveguide settings.
- Expose those settings in the task panel.
- Validate them in preflight.
- Export real waveguide port commands in the script.
- Remove placeholder/legacy waveguide-port export stubs once the real waveguide path is stable.

Recommended first version:

- Start with manual parameter entry.
- Later add face or object picking if needed.

Reason:

This keeps the implementation smaller while still reaching the intended physics workflow.

Commit-sized tasks:

1. Commit 8.1: Add waveguide port properties to the port object model and defaults.
2. Commit 8.2: Extend port task panel UI with waveguide settings and validation hints.
3. Commit 8.3: Extend preflight to validate waveguide-specific requirements.
4. Commit 8.4: Generate waveguide port commands in script export and add tests.
5. Commit 8.5: Remove legacy placeholder waveguide-port branches while preserving working non-waveguide port behavior.

### Phase 9: add sinusoidal excitation support

The coax target also needs sinusoidal excitation, which is currently not fully supported.

This phase should:

- Add sinusoidal excitation as a real supported simulation option.
- Keep Gaussian excitation working.
- Validate excitation parameters properly.
- Export the correct openEMS excitation call.
- Remove temporary unsupported-excitation placeholder branches once sinusoidal export is fully integrated.

Reason:

This is required for the target cable example and should be added only after the base export-and-run path is trustworthy.

Commit-sized tasks:

1. Commit 9.1: Extend simulation model and panel to support sinusoidal parameters.
2. Commit 9.2: Add preflight checks for sinusoidal parameter validity.
3. Commit 9.3: Map sinusoidal mode to the correct openEMS script calls while preserving Gaussian behavior.
4. Commit 9.4: Add tests for both Gaussian and sinusoidal export paths.
5. Commit 9.5: Remove legacy placeholder excitation branches and keep one clean production excitation path set (Gaussian + Sinusoidal).

### Phase 10: build the coaxial-cable reference workflow

Once the previous phases are done, use a coaxial-cable example as the main acceptance test for the MVP.

This phase should include:

- FreeCAD coax geometry.
- Material assignment for conductors and dielectric.
- Absorbing boundary conditions.
- Waveguide excitation at one end.
- Simulation run.
- Saved field output in the results folder.

Reason:

This is the real scientific use case that the MVP should demonstrate.

Commit-sized tasks:

1. Commit 10.1: Add a documented coax geometry setup example in the examples folder.
2. Commit 10.2: Add documented material assignment and boundary setup for the coax case.
3. Commit 10.3: Add documented run steps and expected output files for acceptance.
4. Commit 10.4: Add a final verification checklist specifically for the coax reference workflow.

## What is included in the first MVP

The first MVP should include:

- Geometry created in FreeCAD.
- Analysis object workflow.
- Material assignment to geometry.
- Automatic simulation box.
- Boundary conditions setup.
- Mesh setup tied to the real model.
- Real geometry and material export.
- Automatic preflight before run.
- Consistent FreeCAD to openEMS unit handling.
- Simulation run from FreeCAD.
- Results written to a user-defined folder.
- Field dump output at least for electric fields.

## What is intentionally not in the first MVP

The first MVP does not need to include:

- Full in-FreeCAD postprocessing.
- Voltage and current probe objects as separate first-class tools.
- Every possible excitation family.
- Every possible material model.
- Direct `openEMS.exe` execution mode.

These can come later after the main workflow is working well.

## Suggested verification strategy

Each phase should be small, testable, and easy to deploy.

For every phase:

- Update or add unit tests where possible.
- Verify that FreeCAD can still open the workbench without errors.
- Verify that save and reopen still preserve the new data.
- Verify that export output is stable and understandable.

Important manual checks:

- Assign materials and confirm they remain assigned after reopening the document.
- Inspect generated scripts and confirm real geometry and material commands exist.
- Change geometry size and confirm simulation box and mesh update correctly.
- Verify unit conversion with at least one geometry model created in millimeters.
- Run a simulation and confirm preflight is run automatically first.
- Run a simulation and confirm stdout, stderr, and result files are created.
- Verify the coax example only after waveguide and sinusoidal support are complete.

## File areas that will likely need changes

The most important files for this plan are:

- docs/workbench-description.md
- README.md
- freecad/OpenEMSWorkbench/objects/material_feature.py
- freecad/OpenEMSWorkbench/gui/task_panels/material_panel.py
- freecad/OpenEMSWorkbench/exporter/document_reader.py
- freecad/OpenEMSWorkbench/exporter/script_generator.py
- freecad/OpenEMSWorkbench/exporter/geometry_classifier.py
- freecad/OpenEMSWorkbench/exporter/primitive_mapper.py
- freecad/OpenEMSWorkbench/meshing/__init__.py
- freecad/OpenEMSWorkbench/objects/port_feature.py
- freecad/OpenEMSWorkbench/gui/task_panels/port_panel.py
- freecad/OpenEMSWorkbench/objects/simulation_feature.py
- freecad/OpenEMSWorkbench/gui/task_panels/simulation_panel.py
- freecad/OpenEMSWorkbench/validation/preflight.py
- freecad/OpenEMSWorkbench/execution/__init__.py
- tests/unit/test_preflight.py
- tests/unit/test_exporter_script.py
- tests/unit/test_exporter_pipeline.py

## Final note

The best path is not to jump directly to the most advanced case.

The best path is:

1. Make the current pipeline real and reliable.
2. Make one simple case work fully.
3. Add the missing coax-specific features.
4. Use the coax case as the scientific acceptance test.
5. Later add result viewing inside FreeCAD.

This keeps development incremental, testable, and easier to debug.