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
        simulation={"name": "Sim"},
        grid={"name": "Grid"},
        boundary={"XMin": "PEC", "XMax": "PEC", "YMin": "PEC", "YMax": "PEC", "ZMin": "PEC", "ZMax": "PEC"},
        geometries=[
            GeometryEntry("B", "Box", "box", {"start": [0, 0, 0], "stop": [1, 1, 1]}),
            GeometryEntry("P", "Poly", "polyhedron", {"stl_path": "C:/tmp/p.stl"}),
        ],
    )
    path = generate_openems_script(model, tmp_path / "script.py")
    text = path.read_text(encoding="utf-8")

    assert "import CSXCAD" in text
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
