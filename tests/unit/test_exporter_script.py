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
            GeometryEntry("B", "Box", "box", {"start": [0, 0, 0], "stop": [1, 1, 1]}),
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
    assert "# BOX B" in text
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
