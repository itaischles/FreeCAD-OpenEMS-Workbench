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
