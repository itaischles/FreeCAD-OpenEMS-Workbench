from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class Proxy:
    def __init__(self, proxy_type):
        self.TYPE = proxy_type


class OpenEMSObj:
    def __init__(self, name, proxy_type, **attrs):
        self.Name = name
        self.Label = name
        self.Proxy = Proxy(proxy_type)
        for key, value in attrs.items():
            setattr(self, key, value)


class BoundBox:
    XMin = 0.0
    YMin = 0.0
    ZMin = 0.0
    XMax = 1.0
    YMax = 2.0
    ZMax = 3.0


class Shape:
    BoundBox = BoundBox()

    def exportStl(self, path):
        Path(path).write_text("solid s\nendsolid s\n", encoding="ascii")


class EmptyStlShape:
    BoundBox = BoundBox()

    def exportStl(self, path):
        Path(path).write_text("", encoding="ascii")


class InvalidStlShape:
    BoundBox = BoundBox()

    def exportStl(self, path):
        Path(path).write_text("this is not an stl artifact", encoding="ascii")


class MissingStlShape:
    BoundBox = BoundBox()

    def exportStl(self, path):
        return None


class BinaryStlShape:
    BoundBox = BoundBox()

    def exportStl(self, path):
        header = b"binary-stl-test".ljust(80, b" ")
        triangle_count = (1).to_bytes(4, byteorder="little", signed=False)
        facet = (
            b"\x00\x00\x00\x00"  # normal x
            b"\x00\x00\x00\x00"  # normal y
            b"\x00\x00\x00\x00"  # normal z
            b"\x00\x00\x00\x00"  # v1 x
            b"\x00\x00\x00\x00"  # v1 y
            b"\x00\x00\x00\x00"  # v1 z
            b"\x00\x00\x80\x3f"  # v2 x
            b"\x00\x00\x00\x00"  # v2 y
            b"\x00\x00\x00\x00"  # v2 z
            b"\x00\x00\x00\x00"  # v3 x
            b"\x00\x00\x80\x3f"  # v3 y
            b"\x00\x00\x00\x00"  # v3 z
            b"\x00\x00"            # attribute byte count
        )
        Path(path).write_bytes(header + triangle_count + facet)


class GeoObj:
    def __init__(self, name, type_id, shape=None):
        self.Name = name
        self.Label = name
        self.TypeId = type_id
        self.Shape = shape if shape is not None else Shape()


class Analysis:
    def __init__(self, name, group):
        self.Name = name
        self.Label = name
        self.Group = group


def test_pipeline_generates_script_and_stl(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import export_analysis_dry_run

    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", CoordinateSystem="Cartesian", OutputDirectory=""),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj("Mat", "OpenEMS_Material"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            OpenEMSObj("Port", "OpenEMS_Port", PortNumber=1),
            GeoObj("GeoBox", "Part::Box"),
            GeoObj("GeoComplex", "Part::Feature"),
        ],
    )

    result = export_analysis_dry_run(analysis, tmp_path, "Doc")
    assert result["geometry_count"] == 2
    assert result["primitive_count"] == 1
    assert result["stl_count"] == 1
    assert Path(result["paths"]["script"]).exists()

    script_text = Path(result["paths"]["script"]).read_text(encoding="utf-8")
    assert "AddBox(" in script_text
    assert "# POLYHEDRON GeoComplex" in script_text
    assert "grid.AddLine('x', [0.0, 1.0])" in script_text
    assert "grid.AddLine('y', [0.0, 1.0, 2.0])" in script_text

    stl_dir = Path(result["paths"]["stl_dir"])
    assert (stl_dir / "GeoComplex.stl").exists()


def test_pipeline_direct_only_export_counts(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import export_analysis_dry_run

    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", CoordinateSystem="Cartesian", OutputDirectory=""),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj("Mat", "OpenEMS_Material"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            GeoObj("GeoBoxA", "Part::Box"),
            GeoObj("GeoBoxB", "Part::Box"),
        ],
    )

    result = export_analysis_dry_run(analysis, tmp_path, "Doc")

    assert result["geometry_count"] == 2
    assert result["primitive_count"] == 2
    assert result["stl_count"] == 0


def test_pipeline_fallback_only_export_counts_and_stl_files(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import export_analysis_dry_run

    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", CoordinateSystem="Cartesian", OutputDirectory=""),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj("Mat", "OpenEMS_Material"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            GeoObj("GeoComplexA", "Part::Feature"),
            GeoObj("GeoComplexB", "Part::Feature"),
        ],
    )

    result = export_analysis_dry_run(analysis, tmp_path, "Doc")

    assert result["geometry_count"] == 2
    assert result["primitive_count"] == 0
    assert result["stl_count"] == 2

    stl_dir = Path(result["paths"]["stl_dir"])
    assert (stl_dir / "GeoComplexA.stl").exists()
    assert (stl_dir / "GeoComplexB.stl").exists()


def test_build_export_model_binds_geometry_assignments(tmp_path):
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export
    from OpenEMSWorkbench.exporter.pipeline import _build_export_model

    geo_box = GeoObj("GeoBox", "Part::Box")
    geo_complex = GeoObj("GeoComplex", "Part::Feature")

    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", CoordinateSystem="Cartesian", OutputDirectory=""),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj(
                "MatA",
                "OpenEMS_Material",
                AssignmentPriority=5,
                AssignedGeometry=[geo_box],
            ),
            OpenEMSObj(
                "MatB",
                "OpenEMS_Material",
                AssignmentPriority=9,
                AssignedGeometry=[geo_complex],
            ),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            geo_box,
            geo_complex,
        ],
    )

    extracted = read_analysis_for_export(analysis)
    stl_dir = tmp_path / "stl"
    stl_dir.mkdir(parents=True, exist_ok=True)

    model = _build_export_model(extracted, stl_dir)
    by_name = {entry.object_name: entry for entry in model.geometries}

    assert by_name["GeoBox"].assigned_material_name == "MatA"
    assert by_name["GeoBox"].assignment_priority == 5
    assert by_name["GeoComplex"].assigned_material_name == "MatB"
    assert by_name["GeoComplex"].assignment_priority == 9
    assert by_name["GeoComplex"].stl_artifact is not None
    assert by_name["GeoComplex"].stl_artifact.path.endswith("GeoComplex.stl")
    assert by_name["GeoComplex"].params["stl_path"].endswith("GeoComplex.stl")


def test_build_export_model_exposes_stl_contract_for_fallback_geometry(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import _build_export_model

    geo_complex = GeoObj("GeoComplex", "Part::Feature")
    stl_dir = tmp_path / "stl"
    stl_dir.mkdir(parents=True, exist_ok=True)

    extracted = {
        "analysis_name": "Analysis",
        "simulation": {},
        "grid": {},
        "materials": [],
        "boundary": {},
        "ports": [],
        "dumpboxes": [],
        "geometry_objects": [geo_complex],
        "material_assignments": [
            {"geometry_name": "GeoComplex", "material_name": "MatB", "priority": 9}
        ],
    }

    model = _build_export_model(extracted, stl_dir)

    assert len(model.geometries) == 1
    entry = model.geometries[0]
    assert entry.primitive == "polyhedron"
    assert entry.stl_artifact is not None
    assert entry.stl_artifact.format == "stl"
    assert entry.stl_artifact.path.endswith("GeoComplex.stl")
    assert entry.assigned_material_name == "MatB"
    assert entry.assignment_priority == 9


def test_build_export_model_rejects_conflicting_duplicate_assignments(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import _build_export_model

    geo_box = GeoObj("GeoBox", "Part::Box")
    stl_dir = tmp_path / "stl"
    stl_dir.mkdir(parents=True, exist_ok=True)

    extracted = {
        "analysis_name": "Analysis",
        "simulation": {},
        "grid": {},
        "materials": [],
        "boundary": {},
        "ports": [],
        "dumpboxes": [],
        "geometry_objects": [geo_box],
        "material_assignments": [
            {"geometry_name": "GeoBox", "material_name": "MatA", "priority": 1},
            {"geometry_name": "GeoBox", "material_name": "MatB", "priority": 2},
        ],
    }

    try:
        _build_export_model(extracted, stl_dir)
        assert False, "Expected conflicting material assignments to raise ValueError"
    except ValueError as exc:
        assert "GeoBox" in str(exc)


def test_build_export_model_carries_simulation_box(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import _build_export_model

    geo_box = GeoObj("GeoBox", "Part::Box")
    stl_dir = tmp_path / "stl"
    stl_dir.mkdir(parents=True, exist_ok=True)

    extracted = {
        "analysis_name": "Analysis",
        "simulation": {},
        "grid": {},
        "simulation_box": {
            "XMin": -1.0,
            "YMin": -2.0,
            "ZMin": -3.0,
            "XMax": 4.0,
            "YMax": 5.0,
            "ZMax": 6.0,
            "Margin": 0.0,
        },
        "materials": [],
        "boundary": {},
        "ports": [],
        "dumpboxes": [],
        "geometry_objects": [geo_box],
        "material_assignments": [],
    }

    model = _build_export_model(extracted, stl_dir)

    assert model.simulation_box["XMin"] == -1.0
    assert model.simulation_box["ZMax"] == 6.0


def test_pipeline_rejects_empty_stl_artifact(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import export_analysis_dry_run

    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", CoordinateSystem="Cartesian", OutputDirectory=""),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj("Mat", "OpenEMS_Material"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            GeoObj("GeoComplex", "Part::Feature", shape=EmptyStlShape()),
        ],
    )

    try:
        export_analysis_dry_run(analysis, tmp_path, "Doc")
        assert False, "Expected empty STL artifact to raise ValueError"
    except ValueError as exc:
        assert "empty STL file" in str(exc)


def test_pipeline_rejects_invalid_stl_artifact(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import export_analysis_dry_run

    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", CoordinateSystem="Cartesian", OutputDirectory=""),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj("Mat", "OpenEMS_Material"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            GeoObj("GeoComplex", "Part::Feature", shape=InvalidStlShape()),
        ],
    )

    try:
        export_analysis_dry_run(analysis, tmp_path, "Doc")
        assert False, "Expected invalid STL artifact to raise ValueError"
    except ValueError as exc:
        assert "invalid STL artifact" in str(exc)


def test_pipeline_rejects_missing_stl_artifact_file(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import export_analysis_dry_run

    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", CoordinateSystem="Cartesian", OutputDirectory=""),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj("Mat", "OpenEMS_Material"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            GeoObj("GeoComplex", "Part::Feature", shape=MissingStlShape()),
        ],
    )

    try:
        export_analysis_dry_run(analysis, tmp_path, "Doc")
        assert False, "Expected missing STL artifact to raise ValueError"
    except ValueError as exc:
        assert "missing its STL file" in str(exc)


def test_pipeline_accepts_valid_binary_stl_artifact(tmp_path):
    from OpenEMSWorkbench.exporter.pipeline import export_analysis_dry_run

    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", CoordinateSystem="Cartesian", OutputDirectory=""),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj("Mat", "OpenEMS_Material"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            GeoObj("GeoComplex", "Part::Feature", shape=BinaryStlShape()),
        ],
    )

    result = export_analysis_dry_run(analysis, tmp_path, "Doc")

    assert result["stl_count"] == 1
    stl_path = Path(result["paths"]["stl_dir"]) / "GeoComplex.stl"
    assert stl_path.exists()
    assert stl_path.stat().st_size == 134


def test_run_ready_export_rejects_missing_stl_reader_runtime(monkeypatch, tmp_path):
    from OpenEMSWorkbench.exporter import pipeline
    from OpenEMSWorkbench.execution import runtime_discovery

    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj(
                "Sim",
                "OpenEMS_Simulation",
                CoordinateSystem="Cartesian",
                OutputDirectory="",
                SolverExecutable="C:/Python/python.exe",
            ),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj("Mat", "OpenEMS_Material"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            GeoObj("GeoComplex", "Part::Feature"),
        ],
    )

    monkeypatch.setattr(
        pipeline,
        "build_mesh_for_analysis",
        lambda _analysis: (
            None,
            None,
            type("Mesh", (), {"coordinate_system": "Cartesian", "x": (0.0, 1.0), "y": (0.0, 1.0), "z": (0.0, 1.0), "radial": (), "azimuth": ()})(),
        ),
    )

    monkeypatch.setattr(
        runtime_discovery,
        "inspect_python_runtime",
        lambda executable, timeout_seconds=20: type(
            "RuntimeResult",
            (),
            {"ok": True, "message": "STL reader: unavailable", "capabilities": {"stl_reader": False}},
        )(),
    )

    try:
        pipeline.export_analysis_run_ready(analysis, tmp_path, "Doc")
        assert False, "Expected missing STL reader runtime to raise ValueError"
    except ValueError as exc:
        assert "does not expose the CSXCAD STL reader" in str(exc)


def test_run_ready_export_succeeds_for_valid_stl_with_supported_runtime(monkeypatch, tmp_path):
    from OpenEMSWorkbench.exporter import pipeline
    from OpenEMSWorkbench.execution import runtime_discovery

    geo_complex = GeoObj("GeoComplex", "Part::Feature")
    analysis = Analysis(
        "Analysis",
        [
            OpenEMSObj(
                "Sim",
                "OpenEMS_Simulation",
                CoordinateSystem="Cartesian",
                OutputDirectory="",
                SolverExecutable="C:/Python/python.exe",
            ),
            OpenEMSObj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian"),
            OpenEMSObj(
                "MatCopper",
                "OpenEMS_Material",
                AssignmentPriority=12,
                AssignedGeometry=[geo_complex],
                IsPEC=True,
            ),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            geo_complex,
        ],
    )

    monkeypatch.setattr(
        pipeline,
        "build_mesh_for_analysis",
        lambda _analysis: (
            None,
            None,
            type("Mesh", (), {"coordinate_system": "Cartesian", "x": (0.0, 1.0), "y": (0.0, 1.0), "z": (0.0, 1.0), "radial": (), "azimuth": ()})(),
        ),
    )

    monkeypatch.setattr(
        runtime_discovery,
        "inspect_python_runtime",
        lambda executable, timeout_seconds=20: type(
            "RuntimeResult",
            (),
            {"ok": True, "message": "STL reader: available", "capabilities": {"stl_reader": True}},
        )(),
    )

    result = pipeline.export_analysis_run_ready(analysis, tmp_path, "Doc")

    script_text = Path(result["paths"]["script"]).read_text(encoding="utf-8")
    assert result["stl_count"] == 1
    assert "poly_GeoComplex = _add_polyhedron_reader(mat_0_MatCopper" in script_text
    assert "priority=12" in script_text
    assert "AddPolyhedronReader" in script_text
