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

### Phase 5: generate mesh from the simulation box and export it consistently

The current mesh path still includes generic symmetric behavior, so this phase should replace it with one clean production mesh pipeline tied to the Phase 4 simulation box.

Responsibility split for this phase:

- Simulation object: run and physics settings (excitation, timestep, solver, units).
- Simulation box object: simulation-domain extents and boundary conditions.
- Grid object (kept for now): mesh settings and meshing behavior.

This phase should:

- Generate mesh only inside the simulation box computed in Phase 4.
- Keep the Grid object and update it so it remains the single owner of user-defined mesh resolution and grading settings.
- Snap mesh lines conservatively to analysis solids by aligning to solid bounding-face planes.
- Keep current Grid/mesh naming as-is for this phase, and defer naming cleanup to a later dedicated refactor.
- Display the mesh cleanly in FreeCAD using an object-based preview path with readable behavior for dense meshes.
- Export the same mesh model to the openEMS Python script so preview and export share one source of truth.
- Remove legacy symmetric mesh-generation and duplicate mesh-calculation paths completely after migration.
- Verify each step with automated tests and manual FreeCAD checks.

Reason:

The mesh must represent the real simulation domain and geometry, stay deterministic for testing, and be consistent between FreeCAD preview and openEMS script export.

Commit-sized tasks:

1. Commit 5.1: Clarify and enforce ownership boundaries in code and docs (Simulation = run/physics, Simulation Box = domain, Grid = mesh settings) and keep one active Grid object per analysis.
2. Commit 5.2: Generate mesh strictly inside the simulation-box extents.
3. Commit 5.3: Update Grid-object meshing settings so users configure mesh resolution clearly while preserving backward compatibility.
4. Commit 5.4: Add conservative solid-aware snapping to bounding-face planes while keeping deterministic ordering.
5. Commit 5.5: Implement clean object-based mesh preview behavior in FreeCAD, including dense-mesh readability rules.
6. Commit 5.6: Export mesh lines to the openEMS Python script from the same bounded/snapped mesh model used by preview.
7. Commit 5.7: Remove legacy symmetric mesh-domain logic and duplicate exporter-side mesh-line generators.

Manual verification checks for this phase:

- Check 5.M1: Build an analysis with solids, refresh the simulation box, generate mesh preview, and verify no mesh appears outside the simulation box.
- Check 5.M2: Change only Grid mesh resolution settings and verify mesh density updates as expected.
- Check 5.M3: Verify conservative snapping by confirming mesh lines align with solid bounding faces.
- Check 5.M4: Export and inspect the generated Python script to verify mesh lines match bounded/snapped preview behavior.
- Check 5.M5: Save and reopen the document, then verify mesh settings and preview behavior persist without legacy behavior.

Automated verification checks for this phase:

- Run `pytest tests/unit/test_mesh_generation.py tests/unit/test_exporter_script.py tests/unit/test_exporter_pipeline.py` after each commit-sized task.
- Run `pytest tests/unit/test_analysis_feature.py tests/unit/test_phase2_commands.py tests/unit/test_preflight.py` after changes that touch Grid/simulation ownership wiring, commands, or validation.
- Add/adjust tests to assert boundedness, deterministic snapping behavior, preview/export consistency, and absence of legacy mesh paths.

### Phase 6: set a waveguide port on a simulation-box boundary face

Waveguide support is one of the most important missing parts for the intended coaxial-cable workflow.

This phase should:

- Let the user choose which simulation-box face the waveguide port attaches to.
- Keep the selected boundary face fixed.
- Place the waveguide source plane automatically a small number of mesh cells (default 3) inside the simulation box from that face.
- Show that waveguide source plane in FreeCAD so the user can see exactly where the port is located.
- Place the probing/reference plane exactly one mesh cell farther inward from the source plane in the direction of propagation.
- Keep the simulation box and mesh extents unchanged.
- Read the coax cross-section on that face from the model geometry and material assignments.
- Infer the needed spatial field information from the selected face for the supported coax case.
- Calculate the coax port impedance automatically when `r_in`, `r_out`, and dielectric `epsilon_r` are successfully inferred.
- Calculate and export the spatial electric and magnetic field functions for that waveguide/coax port.
- Export the resulting waveguide/coax port definition from FreeCAD workbench data to the openEMS Python script.
- Remove the current placeholder behavior that says waveguide is unsupported.

Reason:

Waveguide setup is different from excitation setup. This phase is about where the source is attached and what field shape it has in space. It is not yet about the time waveform or source magnitude.

Recommended MVP target:

- Support automatic reading first for a restricted but useful coax case.
- Start with axis-aligned coax geometry that crosses the selected simulation-box face cleanly.
- Keep one explicit three-plane contract: selected boundary face, source plane a few mesh cells inward, and probing/reference plane one mesh cell farther inward along propagation direction.
- Treat the number of inward mesh cells as a controlled waveguide setting that must be validated to avoid strong reflections back into the simulation domain.
- Auto-fill the port impedance (`Z0`) when supported coax geometry/material inference succeeds.
- Generate coaxial waveguide `E` and `H` spatial field functions automatically for the supported case.
- If the geometry on the selected face does not match the supported pattern, stop in preflight with a clear message.

Commit-sized tasks:

1. Commit 6.1: Extend the port object so it stores the selected simulation-box face and the source-plane offset in mesh cells.
2. Commit 6.2: Show a visible waveguide-port plane in FreeCAD at the computed source-plane location so the user can confirm the port position visually.
3. Commit 6.3: Add geometry-reading logic that inspects the selected face and tries to detect a supported coax cross-section.
4. Commit 6.4: Infer `r_in`, `r_out`, coax axis, and dielectric epsilon from the detected geometry and assigned material objects.
5. Commit 6.5: Extend the port panel so the user selects the face and sees a simple detected-geometry summary plus the inward mesh-cell offset setting.
6. Commit 6.6: Replace the current waveguide placeholder error in preflight with real checks for supported coax geometry, valid boundary type, and safe source-plane distance from the selected face.
7. Commit 6.7: Automatically calculate coax port impedance in the workbench when `r_in`, `r_out`, and `epsilon_r` are successfully inferred, and update the port impedance (`Z0`) field.
8. Commit 6.8: Define and enforce the three-plane placement contract: selected simulation-box boundary face, source plane (orange preview plane) a few mesh cells inward, and probing/reference plane exactly one mesh cell farther inward along the propagation direction.
9. Commit 6.9: Calculate and export the coaxial waveguide spatial field functions (`E` and `H`) for the supported axis-aligned coax case.
10. Commit 6.10: Implement the full exporter path from FreeCAD workbench waveguide/coax port data to openEMS script generation, and add tests for valid and invalid cases.

### Phase 7: export STL fallback geometry through the openEMS STL reader

The exporter already writes `.stl` files for unsupported geometry, but that path still stops short of creating real openEMS geometry in the generated Python script.

This phase should:

- Keep boxes and cylinders on the current direct primitive-export path.
- Export unsupported FreeCAD solid geometry as `.stl` files through the existing fallback path.
- Feed those exported `.stl` files into the openEMS/CSXCAD polyhedron reader when the installed Python runtime supports it.
- Preserve assigned material binding and primitive priority for STL-backed geometry the same way direct primitives already do.
- Validate that runnable export is only allowed when the selected openEMS/CSXCAD Python runtime actually supports the STL reader path.
- Fail clearly when the STL reader is unavailable or the exported STL artifact is missing or unusable.

Reason:

The repository already has a partial STL fallback path, but not a real simulation-geometry path for those fallback files. This phase closes that gap while keeping scope focused and compatible with the existing exporter design.

Recommended MVP target:

- Support STL-backed geometry only for shapes that already fall through the existing fallback path.
- Use the documented Python reader-backed polyhedron path first, not manual STL triangle parsing.
- Treat STL reader availability as a runtime capability that must be checked explicitly.
- If the runtime does not provide the STL reader, stop with a clear preflight or export error rather than generating a misleading placeholder script.

Commit-sized tasks:

1. Commit 7.1: Define the STL-backed export contract so fallback geometries carry the STL path, assigned material, and priority cleanly through the export model.
2. Commit 7.2: Extend runtime capability discovery so runnable export can detect whether the installed openEMS/CSXCAD Python binding supports the STL reader path.
3. Commit 7.3: Replace the current comment-only polyhedron script output with real CSXCAD STL-reader-backed geometry emission in the generated Python script.
4. Commit 7.4: Add export and preflight checks for reader availability, missing STL files, empty or invalid STL artifacts, and clear user-facing failure messages.
5. Commit 7.5: Add tests for valid STL-backed export, preserved material and priority binding, reader-unavailable behavior, and invalid artifact handling.

### Phase 8: add explicit temporal excitation behavior and automatic timestep budgeting

The coax workflow also needs explicit control of source behavior in time, but this must stay separate from the Phase 6 waveguide spatial setup.

This phase should:

- Let the user choose excitation type in the simulation task panel (Sinusoid, Gaussian, and a modular custom-expression path).
- Show excitation parameters that depend on the selected functional form.
- Keep `f_max` mandatory even when the waveform is fully defined, because it is still needed for solver frequency-content and sampling/stability context.
- Let the user define a physical maximum simulation time (for example `100 ns`) instead of manually guessing timestep count.
- Compute a stable timestep estimate from mesh constraints and compute `NrTS = ceil(T_max / dt)` automatically.
- Store and show the computed timestep and computed timestep budget on the simulation object so users can inspect what will be used.
- Export one consistent excitation path to openEMS while preserving compatibility with current behavior.

Reason:

This phase is about temporal behavior and simulation duration budgeting. It should remain independent from Phase 6, which defines where the source is located and what spatial field pattern is injected.

Recommended MVP target:

- Introduce one internal waveform abstraction in the workbench so new waveform families can be added without changing exporter architecture.
- Use native openEMS calls for built-in Sinusoid and Gaussian in MVP (`SetSinusExcite`, `SetGaussExcite`) to keep behavior predictable and lower risk.
- Add a custom-expression backend (`SetCustomExcite`) as the modular extension path, with explicit safeguards:
- Always set a bounded timestep count (`NrTS`) for custom excitation to avoid unbounded precomputation.
- Encode custom expression payloads in the format expected by the Python binding.
- Export both `NrTS` and `MaxTime` from the same user-selected `T_max` contract for robust run limiting.

Commit-sized tasks:

1. Commit 8.1: Extend the simulation model and task panel with excitation-type dropdown, per-type parameter groups, mandatory `f_max` (Hz), and user-defined physical `T_max` (sec).
2. Commit 8.2: Add deterministic timestep-budget computation (`dt`, `NrTS`) from mesh and `T_max`, and expose computed values in the simulation object/panel.
3. Commit 8.3: Add preflight checks for per-type parameter validity, mandatory `f_max`, valid `T_max`, and finite computed `dt`/`NrTS`.
4. Commit 8.4: Refactor exporter excitation architecture to use one internal waveform abstraction with pluggable backends (native Sinusoid/Gaussian now, custom-expression backend enabled).
5. Commit 8.5: Export run limits consistently from the new contract (`NrTS` derived from `T_max` and computed `dt`, plus exported `MaxTime`) and keep `EndCriteria` behavior.
6. Commit 8.6: Add tests for panel conditional behavior, timestep-budget calculation, preflight validation, and script generation for Sinusoid/Gaussian/custom backends.
7. Commit 8.7: Remove legacy placeholder excitation branches and finalize one clean excitation pipeline with backward compatibility for existing documents.

### Phase 9: make dump boxes generate real field output

DumpBox objects already exist, but they are still mostly placeholders in the exported script.

This phase should:

- Export real field-dump definitions.
- Save the dump results into the chosen results folder.
- Support at least the electric field first.
- Remove placeholder dumpbox export behavior once real dump commands are implemented.

Reason:

Field dump output is important for the MVP, but it should come after the core waveguide and excitation setup is in place.

Commit-sized tasks:

1. Commit 9.1: Extend dumpbox export model with explicit dump type and frequency handling.
2. Commit 9.2: Generate real openEMS field-dump commands for at least electric-field outputs.
3. Commit 9.3: Ensure dump output paths are created under the user-defined results folder.
4. Commit 9.4: Add tests that verify dump commands and output path generation.
5. Commit 9.5: Remove legacy placeholder dumpbox script stubs and temporary compatibility branches.

### Phase 10: build the coaxial-cable reference workflow

Once the previous phases are done, use a coaxial-cable example as the main acceptance test for the scientific workflow.

This phase should include:

- FreeCAD coax geometry.
- Material assignment for conductors and dielectric.
- Absorbing boundary conditions.
- Waveguide setup on one selected boundary face.
- Excitation setup.
- Field dump output.
- Documented expected export artifacts and output files.

Reason:

This is the real scientific use case that the MVP should demonstrate.

Commit-sized tasks:

1. Commit 10.1: Add a documented coax geometry setup example in the examples folder.
2. Commit 10.2: Add documented material assignment, boundary setup, waveguide setup, and excitation setup for the coax case.
3. Commit 10.3: Add documented expected export artifacts and output files for acceptance.
4. Commit 10.4: Add a final verification checklist specifically for the coax reference workflow.

### Phase 11: stabilize one full end-to-end runnable MVP case

After the missing building blocks are in place, finish by proving that one complete workflow runs from start to finish.

This phase should:

- Run preflight automatically before every simulation run.
- Block simulation launch cleanly when setup is invalid.
- Export a real script.
- Run successfully from the FreeCAD workflow.
- Produce logs, solver output, and result files.
- Serve as the final integration check for the MVP.

Reason:

The full end-to-end runnable case makes more sense as the last integration phase, after the needed setup features are already implemented.

Commit-sized tasks:

1. Commit 11.1: Enforce automatic preflight invocation before simulation run command executes.
2. Commit 11.2: Improve run-time reporting so preflight failures are shown clearly and block solver launch.
3. Commit 11.3: Add one stable end-to-end example that passes preflight, exports, runs, and produces output files.
4. Commit 11.4: Add execution tests covering auto-preflight, run gating behavior, and final MVP workflow stability.

## What is included in the first MVP

The first MVP should include:

- Geometry created in FreeCAD.
- Analysis object workflow.
- Material assignment to geometry.
- Automatic simulation box.
- Boundary conditions setup.
- Mesh setup tied to the real model.
- Waveguide setup on a selected simulation-box face.
- STL-backed fallback geometry export when supported by the selected openEMS runtime.
- Excitation setup with supported time-profile options.
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
- Inspect generated scripts and confirm real geometry, material commands, and STL-backed reader geometry commands exist when fallback export is used.
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
- freecad/OpenEMSWorkbench/exporter/stl_fallback.py
- freecad/OpenEMSWorkbench/meshing/__init__.py
- freecad/OpenEMSWorkbench/objects/port_feature.py
- freecad/OpenEMSWorkbench/gui/task_panels/port_panel.py
- freecad/OpenEMSWorkbench/objects/simulation_feature.py
- freecad/OpenEMSWorkbench/gui/task_panels/simulation_panel.py
- freecad/OpenEMSWorkbench/validation/preflight.py
- freecad/OpenEMSWorkbench/execution/__init__.py
- freecad/OpenEMSWorkbench/execution/runtime_discovery.py
- tests/unit/test_preflight.py
- tests/unit/test_exporter_script.py
- tests/unit/test_exporter_pipeline.py

## Final note

The best path is not to jump directly to the most advanced case.

The best path is:

1. Make the current pipeline real and reliable.
2. Add the missing coax-specific setup features in a clear order.
3. Use the coax case as the scientific acceptance workflow.
4. Stabilize one full end-to-end runnable MVP case.
5. Later add result viewing inside FreeCAD.

This keeps development incremental, testable, and easier to debug.