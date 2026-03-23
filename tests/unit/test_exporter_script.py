from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def _default_mesh_lines() -> dict:
    return {
        "coordinate_system": "Cartesian",
        "x": [0.0, 0.5, 1.0],
        "y": [0.0, 0.5, 1.0],
        "z": [0.0, 0.5, 1.0],
    }


def test_script_generator_writes_expected_lines(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel, GeometryEntry, StlArtifact
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={
            "name": "Sim",
            "NumberOfTimeSteps": 1000,
            "EndCriteria": 1e-4,
            "ExcitationType": "Gaussian",
            "ExcitationF0": 1e9,
            "ExcitationFc": 5e8,
        },
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
        materials=[
            {"name": "Copper", "IsPEC": True, "EpsilonR": 1.0, "MuR": 1.0, "Kappa": 0.0},
            {"name": "FR4", "IsPEC": False, "EpsilonR": 4.2, "MuR": 1.0, "Kappa": 0.02},
        ],
        boundary={"XMin": "PEC", "XMax": "PEC", "YMin": "PEC", "YMax": "PEC", "ZMin": "PEC", "ZMax": "PEC"},
        ports=[
            {
                "name": "P1",
                "PortType": "Lumped",
                "PortNumber": 1,
                "Resistance": 50.0,
                "Excite": True,
                "PropagationDirection": "+z",
                "PortStartX": 0.0,
                "PortStartY": 0.0,
                "PortStartZ": 0.0,
                "PortStopX": 0.0,
                "PortStopY": 0.0,
                "PortStopZ": 1.0,
            }
        ],
        geometries=[
            GeometryEntry(
                "B",
                "Box",
                "box",
                {"start": [0, 0, 0], "stop": [1, 1, 1]},
                assigned_material_name="Copper",
                assignment_priority=7,
            ),
            GeometryEntry(
                "C",
                "Cyl",
                "cylinder",
                {"base": [1, 2, 3], "radius": 0.5, "height": 4},
                assigned_material_name="FR4",
                assignment_priority=3,
            ),
            GeometryEntry(
                "P",
                "Poly",
                "polyhedron",
                assigned_material_name="Copper",
                assignment_priority=11,
                stl_artifact=StlArtifact(path="C:/tmp/p.stl"),
            ),
        ],
    )
    path = generate_openems_script(model, tmp_path / "script.py")
    text = path.read_text(encoding="utf-8")

    assert "import CSXCAD" in text
    assert "import sys" in text
    assert "OPENEMS_INSTALL_PATH" in text
    assert "OPENEMS_PYTHONPATH" in text
    assert "sys.path.insert(0, _text)" in text
    assert "grid.AddLine('x'" in text
    assert "grid.AddLine('y'" in text
    assert "grid.AddLine('z'" in text
    assert "FDTD.SetGaussExcite(" in text
    assert "AddLumpedPort(" in text
    assert "CSX.AddMetal('Copper')" in text
    assert "CSX.AddMaterial('FR4')" in text
    assert "SetMaterialProperty(epsilon=4.2, mue=1.0, kappa=0.02)" in text
    assert "AddBox([0.0, 0.0, 0.0], [1.0, 1.0, 1.0], priority=7)" in text
    assert "AddCylinder([1.0, 2.0, 3.0], [1.0, 2.0, 7.0], 0.5, priority=3)" in text
    assert "_phase33_unassigned_prop" not in text
    assert "from CSXCAD import CSPrimitives" in text
    assert "def _add_polyhedron_reader(prop, stl_path, priority):" in text
    assert "poly_P = _add_polyhedron_reader(mat_0_Copper, 'C:/tmp/p.stl', priority=11)" in text
    assert "AddPolyhedronReader" in text
    assert "# BOX B" in text
    assert "# CYLINDER C" in text
    assert "# POLYHEDRON P" in text
    assert "Dry-run export: model assembled; no FDTD.Run() was executed." in text


def test_script_generator_uses_unassigned_fallback_for_missing_polyhedron_binding(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel, GeometryEntry, StlArtifact
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"ExcitationType": "Gaussian", "ExcitationF0": 1e9, "ExcitationFc": 5e8},
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
        materials=[{"name": "Copper", "IsPEC": True}],
        geometries=[
            GeometryEntry(
                "P",
                "Poly",
                "polyhedron",
                assigned_material_name="MissingMat",
                assignment_priority=6,
                stl_artifact=StlArtifact(path="C:/tmp/p.stl"),
            )
        ],
    )

    path = generate_openems_script(model, tmp_path / "script_missing_poly.py")
    text = path.read_text(encoding="utf-8")

    assert "_phase33_unassigned_prop = CSX.AddMaterial('_phase33_unassigned')" in text
    assert "poly_P = _add_polyhedron_reader(_phase33_unassigned_prop, 'C:/tmp/p.stl', priority=6)" in text


def test_script_generator_writes_run_lines_when_runnable(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"name": "Sim"},
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
    )
    path = generate_openems_script(
        model,
        tmp_path / "script_run.py",
        runnable=True,
        run_output_dir=tmp_path / "run_out",
    )
    text = path.read_text(encoding="utf-8")

    assert "FDTD.Run(" in text
    assert "sim_path = Path(" in text


def test_script_generator_converts_signed_port_direction(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"ExcitationType": "Gaussian", "ExcitationF0": 1e9, "ExcitationFc": 5e8},
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
        ports=[
            {
                "name": "P1",
                "PortType": "Lumped",
                "PortNumber": 1,
                "Resistance": 50.0,
                "Excite": True,
                "PropagationDirection": "+z",
                "PortStartX": 0.0,
                "PortStartY": 0.0,
                "PortStartZ": 0.0,
                "PortStopX": 0.0,
                "PortStopY": 0.0,
                "PortStopZ": 1.0,
            }
        ],
    )
    path = generate_openems_script(model, tmp_path / "script.py")
    text = path.read_text(encoding="utf-8")

    assert "'+z'" not in text
    assert "'z'" in text


def test_script_generator_uses_unassigned_fallback_for_missing_binding(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel, GeometryEntry
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"ExcitationType": "Gaussian", "ExcitationF0": 1e9, "ExcitationFc": 5e8},
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
        materials=[{"name": "Copper", "IsPEC": True}],
        geometries=[
            GeometryEntry(
                "B",
                "Box",
                "box",
                {"start": [0, 0, 0], "stop": [1, 1, 1]},
                assigned_material_name="MissingMat",
                assignment_priority=4,
            )
        ],
    )

    path = generate_openems_script(model, tmp_path / "script_missing.py")
    text = path.read_text(encoding="utf-8")

    assert "_phase33_unassigned_prop = CSX.AddMaterial('_phase33_unassigned')" in text
    assert "_phase33_unassigned_prop.AddBox([0.0, 0.0, 0.0], [1.0, 1.0, 1.0], priority=4)" in text


def test_script_generator_normalizes_delta_unit_to_mm_contract(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"DeltaUnit": 1.0},
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
    )

    path = generate_openems_script(model, tmp_path / "script_units.py")
    text = path.read_text(encoding="utf-8")

    assert "grid.SetDeltaUnit(0.001)" in text
    assert "Unit contract:" in text


def test_script_generator_scales_geometry_to_selected_delta_unit(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel, GeometryEntry
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"DeltaUnit": 1.0, "FreeCADLengthUnitName": "in"},
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
        geometries=[
            GeometryEntry(
                "B",
                "Box",
                "box",
                {"start": [0, 0, 0], "stop": [1000, 1000, 1000]},
            )
        ],
    )

    path = generate_openems_script(model, tmp_path / "script_scaled.py")
    text = path.read_text(encoding="utf-8")

    assert "grid.SetDeltaUnit(0.001)" in text
    assert "AddBox([0.0, 0.0, 0.0], [1000.0, 1000.0, 1000.0], priority=0)" in text


def test_script_generator_prefers_model_mesh_lines_over_synthetic_axis(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"DeltaUnit": 0.001},
        grid={"MeshBaseStep": 0.1, "MeshMaxStep": 0.2},
        mesh_lines={
            "coordinate_system": "Cartesian",
            "x": [0.0, 1.25, 2.5],
            "y": [0.0, 3.0],
            "z": [-1.0, 0.0, 4.0],
        },
    )

    path = generate_openems_script(model, tmp_path / "script_mesh_lines.py")
    text = path.read_text(encoding="utf-8")

    assert "grid.AddLine('x', [0.0, 1.25, 2.5])" in text
    assert "grid.AddLine('y', [0.0, 3.0])" in text
    assert "grid.AddLine('z', [-1.0, 0.0, 4.0])" in text


def test_script_generator_rejects_missing_mesh_lines(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"DeltaUnit": 0.001},
        grid={"name": "Grid"},
    )

    try:
        generate_openems_script(model, tmp_path / "script_missing_mesh.py")
        assert False, "Expected missing mesh-lines to raise ValueError"
    except ValueError as exc:
        assert "missing mesh lines" in str(exc).lower()


def test_script_generator_exports_tem_field_functions_for_waveguide_coax(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"ExcitationType": "Gaussian", "ExcitationF0": 1e9, "ExcitationFc": 5e8},
        grid={"name": "Grid"},
        simulation_box={
            "XMin": -5.0,
            "XMax": 5.0,
            "YMin": -5.0,
            "YMax": 5.0,
            "ZMin": 0.0,
            "ZMax": 5.0,
        },
        mesh_lines={
            "coordinate_system": "Cartesian",
            "x": [-5.0, 0.0, 5.0],
            "y": [-5.0, 0.0, 5.0],
            "z": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        },
        ports=[
            {
                "name": "PortWG",
                "PortType": "Waveguide",
                "PortNumber": 1,
                "PropagationDirection": "+z",
                "SimulationBoxFace": "ZMin",
                "SourcePlaneOffsetCells": 3,
                "WaveguidePlaneContract": {
                    "selected_face": "ZMin",
                    "source_offset_cells": 3,
                    "reference_offset_cells": 4,
                },
                "WaveguideFaceGeometry": {
                    "status": "supported",
                    "inner": {"center": [0.0, 0.0, 2.5]},
                    "outer": {"center": [0.0, 0.0, 2.5]},
                },
                "WaveguideCoaxInference": {
                    "status": "supported",
                    "axis": "z",
                    "r_in": 1.0,
                    "r_out": 2.0,
                    "dielectric_epsilon_r": 2.2,
                    "z0_ohm": 28.039184028017946,
                },
            }
        ],
    )

    path = generate_openems_script(model, tmp_path / "script_waveguide_tem.py")
    text = path.read_text(encoding="utf-8")

    assert "def port_1_coax_tem_E(x, y, z):" in text
    assert "def port_1_coax_tem_H(x, y, z):" in text
    assert "e_mag = 1.0 / (rho * port_1_coax_tem_ln_ba)" in text
    assert "h_mag = 1.0 / (2.0 * math.pi * port_1_coax_tem_z0 * rho)" in text
    assert "'source_plane': 3.0" in text
    assert "'reference_plane': 4.0" in text
    assert "'E_func': port_1_coax_tem_E" in text
    assert "'E_expr': port_1_coax_tem_E_expr" in text
    assert "'H_func': port_1_coax_tem_H" in text
    assert "'H_expr': port_1_coax_tem_H_expr" in text
    assert "def _add_waveguide_port(fdtd, number, start, stop, direction, e_func, h_func, e_expr, h_expr, kc, excite):" in text
    assert "AddWaveGuidePort(number, start, stop, direction, e_expr, h_expr, kc, excite)" in text
    assert "port_1_waveguide = _add_waveguide_port(FDTD, 1" in text
    assert "port_1_waveguide_reference_start = [-5.0, -5.0, 4.0]" in text
    assert "port_1_waveguide_reference_stop = [5.0, 5.0, 4.0]" in text


def test_script_generator_skips_waveguide_port_export_when_inference_is_unsupported(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"ExcitationType": "Gaussian", "ExcitationF0": 1e9, "ExcitationFc": 5e8},
        grid={"name": "Grid"},
        simulation_box={
            "XMin": -5.0,
            "XMax": 5.0,
            "YMin": -5.0,
            "YMax": 5.0,
            "ZMin": 0.0,
            "ZMax": 5.0,
        },
        mesh_lines={
            "coordinate_system": "Cartesian",
            "x": [-5.0, 0.0, 5.0],
            "y": [-5.0, 0.0, 5.0],
            "z": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        },
        ports=[
            {
                "name": "PortWG",
                "PortType": "Waveguide",
                "PortNumber": 1,
                "PropagationDirection": "+z",
                "SimulationBoxFace": "ZMin",
                "SourcePlaneOffsetCells": 3,
                "WaveguideCoaxInference": {
                    "status": "unsupported",
                    "reason": "dielectric_material_not_found",
                },
            }
        ],
    )

    path = generate_openems_script(model, tmp_path / "script_waveguide_invalid.py")
    text = path.read_text(encoding="utf-8")

    assert "TEM field export skipped" in text
    assert "port_1_waveguide = _add_waveguide_port(" not in text


def test_script_generator_emits_sinusoid_excitation_backend(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={
            "ExcitationType": "Sinusoid",
            "ExcitationFMax": 3e9,
            "SinusoidFrequency": 2.5e9,
            "SinusoidAmplitude": 1.2,
            "SinusoidPhaseDeg": 30.0,
        },
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
    )

    path = generate_openems_script(model, tmp_path / "script_sinusoid.py")
    text = path.read_text(encoding="utf-8")

    assert "# Excitation backend: Sinusoid (f_max=3000000000.0)" in text
    assert "FDTD.SetSinusExcite(2500000000.0)" in text
    assert "Sinusoid parameters: amplitude=1.2, phase_deg=30.0" in text


def test_script_generator_accepts_legacy_sinusoidal_alias(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={
            "ExcitationType": "Sinusoidal",
            "ExcitationFMax": 3e9,
            "SinusoidFrequency": 2.5e9,
        },
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
    )

    path = generate_openems_script(model, tmp_path / "script_sinusoidal_alias.py")
    text = path.read_text(encoding="utf-8")

    assert "# Excitation backend: Sinusoid" in text
    assert "FDTD.SetSinusExcite(2500000000.0)" in text


def test_script_generator_emits_custom_excitation_backend(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={
            "ExcitationType": "Custom",
            "ExcitationFMax": 4e9,
            "CustomExcitationExpression": "sin(2*pi*1e9*t)",
        },
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
    )

    path = generate_openems_script(model, tmp_path / "script_custom.py")
    text = path.read_text(encoding="utf-8")

    assert "# Excitation backend: Custom (f_max=4000000000.0)" in text
    assert "custom_excitation_expression = 'sin(2*pi*1e9*t)'" in text
    assert "_set_custom_excite = getattr(FDTD, 'SetCustomExcite', None)" in text
    assert "Unable to call SetCustomExcite with supported signatures" in text


def test_script_generator_exports_run_limit_contract_with_max_time(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={
            "NumberOfTimeSteps": 2000,
            "ComputedNumberOfTimeSteps": 100,
            "ComputedTimeStep": 1e-9,
            "MaxSimulationTime": 50e-9,
            "EndCriteria": 1e-6,
            "ExcitationType": "Gaussian",
            "ExcitationF0": 1e9,
            "ExcitationFc": 5e8,
        },
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
    )

    path = generate_openems_script(model, tmp_path / "script_run_limits.py")
    text = path.read_text(encoding="utf-8")

    # NrTS must come from ceil(T_max / dt) = ceil(50e-9 / 1e-9) = 50.
    assert "FDTD = openEMS.openEMS(NrTS=50, EndCriteria=1e-06)" in text
    assert "# Run limit contract: NrTS=50, MaxTime=5e-08 sec" in text
    assert "max_time_sec = 5e-08" in text
    assert "_set_max_time = getattr(FDTD, 'SetMaxTime', None)" in text
    assert "Unable to call SetMaxTime with supported signatures" in text


def test_script_generator_emits_time_domain_e_field_dump_plane(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"ExcitationType": "Gaussian", "ExcitationF0": 1e9, "ExcitationFc": 5e8},
        grid={"name": "Grid"},
        simulation_box={
            "XMin": -5.0,
            "XMax": 5.0,
            "YMin": -2.0,
            "YMax": 2.0,
            "ZMin": 0.0,
            "ZMax": 10.0,
        },
        mesh_lines=_default_mesh_lines(),
        dumpboxes=[
            {
                "name": "Dump1",
                "DumpType": "EField",
                "DumpMode": "TimeDomain",
                "PlaneAxis": "Y",
                "Enabled": True,
            }
        ],
    )

    path = generate_openems_script(model, tmp_path / "script_dump_plane.py")
    text = path.read_text(encoding="utf-8")

    assert "dump_path = sim_path / 'dump'" in text
    assert "def _add_e_field_time_dump_plane(csx, dump_directory, start, stop):" in text
    assert "# DUMP Dump1: EField TimeDomain plane axis=Y" in text
    assert "dump_Dump1 = _add_e_field_time_dump_plane(CSX, str(dump_path)," in text


def test_script_generator_skips_disabled_dump_plane(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"ExcitationType": "Gaussian", "ExcitationF0": 1e9, "ExcitationFc": 5e8},
        grid={"name": "Grid"},
        mesh_lines=_default_mesh_lines(),
        dumpboxes=[
            {
                "name": "DumpDisabled",
                "DumpType": "EField",
                "DumpMode": "TimeDomain",
                "PlaneAxis": "Z",
                "Enabled": False,
            }
        ],
    )

    path = generate_openems_script(model, tmp_path / "script_dump_disabled.py")
    text = path.read_text(encoding="utf-8")

    assert "# DUMP DumpDisabled: disabled" in text
    assert "dump_DumpDisabled = _add_e_field_time_dump_plane" not in text
