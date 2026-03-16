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


class GeoObj:
    def __init__(self, name, type_id):
        self.Name = name
        self.Label = name
        self.TypeId = type_id
        self.Shape = Shape()


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
