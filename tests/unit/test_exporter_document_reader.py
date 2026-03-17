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


class GeoObj:
    def __init__(self, name):
        self.Name = name
        self.Label = name
        self.Shape = object()


class _BoundBox:
    def __init__(self, xmin, ymin, zmin, xmax, ymax, zmax):
        self.XMin = xmin
        self.YMin = ymin
        self.ZMin = zmin
        self.XMax = xmax
        self.YMax = ymax
        self.ZMax = zmax


class _ShapeWithBoundBox:
    def __init__(self, bb):
        self.BoundBox = bb


class GeoObjWithBounds:
    def __init__(self, name, xmin, ymin, zmin, xmax, ymax, zmax):
        self.Name = name
        self.Label = name
        self.Shape = _ShapeWithBoundBox(_BoundBox(xmin, ymin, zmin, xmax, ymax, zmax))


class Analysis:
    def __init__(self, group):
        self.Name = "Analysis"
        self.Label = "Analysis"
        self.Group = group


def test_document_reader_emits_material_assignment_metadata():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    geo_a = GeoObj("GeoA")
    geo_b = GeoObj("GeoB")

    mat = OpenEMSObj(
        "Material1",
        "OpenEMS_Material",
        EpsilonR=2.1,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=False,
        AssignmentPriority=7,
        AssignedGeometry=[geo_b, geo_a, geo_a],
    )

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation"),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            mat,
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            geo_a,
            geo_b,
        ]
    )

    extracted = read_analysis_for_export(analysis)

    assert len(extracted["materials"]) == 1
    material = extracted["materials"][0]
    assert material["name"] == "Material1"
    assert material["AssignmentPriority"] == 7
    assert material["AssignedGeometryNames"] == ["GeoA", "GeoB"]

    assert extracted["material_assignments"] == [
        {"geometry_name": "GeoA", "material_name": "Material1", "priority": 7},
        {"geometry_name": "GeoB", "material_name": "Material1", "priority": 7},
    ]


def test_document_reader_handles_missing_assignment_fields():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    mat = OpenEMSObj(
        "Material2",
        "OpenEMS_Material",
        EpsilonR=1.0,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=True,
    )

    analysis = Analysis([
        OpenEMSObj("Sim", "OpenEMS_Simulation"),
        OpenEMSObj("Grid", "OpenEMS_Grid"),
        mat,
        OpenEMSObj("Bnd", "OpenEMS_Boundary"),
    ])

    extracted = read_analysis_for_export(analysis)

    material = extracted["materials"][0]
    assert material["AssignmentPriority"] == 0
    assert material["AssignedGeometryNames"] == []
    assert extracted["material_assignments"] == []


def test_document_reader_computes_simulation_box_with_margin_and_skips_helper_box():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    geo_a = GeoObjWithBounds("GeoA", 0.0, 0.0, 0.0, 10.0, 10.0, 5.0)
    geo_b = GeoObjWithBounds("GeoB", -2.0, 1.0, -1.0, 3.0, 8.0, 2.0)
    helper_box = GeoObjWithBounds("OpenEMSSimulationBox", -100, -100, -100, 100, 100, 100)
    helper_box.OpenEMSSimulationBox = True

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.5),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            geo_a,
            geo_b,
            helper_box,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    sim_box = extracted["simulation_box"]

    assert sim_box["XMin"] == -2.5
    assert sim_box["YMin"] == -0.5
    assert sim_box["ZMin"] == -1.5
    assert sim_box["XMax"] == 10.5
    assert sim_box["YMax"] == 10.5
    assert sim_box["ZMax"] == 5.5
    assert sim_box["Margin"] == 0.5

    geometry_names = [obj.Name for obj in extracted["geometry_objects"]]
    assert geometry_names == ["GeoA", "GeoB"]


def test_document_reader_uses_simulation_box_margin_property_when_present():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    geo_a = GeoObjWithBounds("GeoA", 0.0, 0.0, 0.0, 10.0, 10.0, 5.0)
    geo_b = GeoObjWithBounds("GeoB", -2.0, 1.0, -1.0, 3.0, 8.0, 2.0)
    helper_box = GeoObjWithBounds("OpenEMSSimulationBox", -100, -100, -100, 100, 100, 100)
    helper_box.OpenEMSSimulationBox = True
    helper_box.Margin = 2.0

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.5),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
            geo_a,
            geo_b,
            helper_box,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    sim_box = extracted["simulation_box"]

    assert sim_box["XMin"] == -4.0
    assert sim_box["YMin"] == -2.0
    assert sim_box["ZMin"] == -3.0
    assert sim_box["XMax"] == 12.0
    assert sim_box["YMax"] == 12.0
    assert sim_box["ZMax"] == 7.0
    assert sim_box["Margin"] == 2.0


