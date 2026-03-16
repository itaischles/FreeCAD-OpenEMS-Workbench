from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_script_generator_writes_expected_lines(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel, GeometryEntry
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
            GeometryEntry("P", "Poly", "polyhedron", {"stl_path": "C:/tmp/p.stl"}),
        ],
    )
    path = generate_openems_script(model, tmp_path / "script.py")
    text = path.read_text(encoding="utf-8")

    assert "import CSXCAD" in text
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
    assert "# BOX B" in text
    assert "# CYLINDER C" in text
    assert "# POLYHEDRON P" in text


def test_script_generator_writes_run_lines_when_runnable(tmp_path):
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script

    model = ExportModel(
        analysis_name="A1",
        simulation={"name": "Sim"},
        grid={"name": "Grid"},
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
