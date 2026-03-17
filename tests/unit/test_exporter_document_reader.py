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


class _FakeDocument:
    def __init__(self, objects=None):
        self.Objects = list(objects or [])
        self.add_calls = 0

    def addObject(self, _type, name):
        self.add_calls += 1
        obj = SimBoxObj()
        obj.Name = name
        obj.Label = name
        self.Objects.append(obj)
        return obj


class _AnalysisWithDocument(Analysis):
    def __init__(self, group, document):
        super().__init__(group)
        self.Document = document

    def addObject(self, member):
        if member not in self.Group:
            self.Group.append(member)


class SimBoxObj:
    def __init__(self):
        self._properties = {}
        self.OpenEMSSimulationBox = True

    def addProperty(self, prop_type, prop_name, group, description):
        self._properties[prop_name] = {
            "type": prop_type,
            "group": group,
            "description": description,
        }


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


def test_simulation_box_boundary_properties_are_initialized_and_readable():
    from OpenEMSWorkbench.exporter.document_reader import (
        ensure_simulation_box_properties,
        read_simulation_box_boundary_settings,
    )

    box = SimBoxObj()

    ensure_simulation_box_properties(box, default_margin=0.0)
    boundaries = read_simulation_box_boundary_settings(box)

    assert boundaries["XMin"] == "PML_8"
    assert boundaries["XMax"] == "PML_8"
    assert boundaries["YMin"] == "PML_8"
    assert boundaries["YMax"] == "PML_8"
    assert boundaries["ZMin"] == "PML_8"
    assert boundaries["ZMax"] == "PML_8"
    assert boundaries["PMLCells"] == 8

    box.BoundaryXMin = "PEC"
    box.BoundaryYMax = "MUR"
    boundaries = read_simulation_box_boundary_settings(box)
    assert boundaries["XMin"] == "PEC"
    assert boundaries["YMax"] == "MUR"


def test_refresh_reuses_existing_document_simulation_box_without_duplicates():
    from OpenEMSWorkbench.exporter.document_reader import refresh_simulation_box_for_analysis

    geo = GeoObjWithBounds("GeoA", 0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    sim = OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0)

    existing_box = SimBoxObj()
    existing_box.Name = "OpenEMSSimulationBox"
    existing_box.Label = "openEMS Simulation Box"
    existing_box.OpenEMSSimulationBox = True

    doc = _FakeDocument(objects=[existing_box])
    analysis = _AnalysisWithDocument([sim, geo], doc)

    box = refresh_simulation_box_for_analysis(analysis)

    assert box["XMin"] == 0.0
    assert doc.add_calls == 0
    assert sum(1 for o in doc.Objects if bool(getattr(o, "OpenEMSSimulationBox", False))) == 1
    assert existing_box in analysis.Group


def test_document_reader_uses_simulation_box_boundaries_for_export():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    geo = GeoObjWithBounds("GeoA", 0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    helper_box = GeoObjWithBounds("OpenEMSSimulationBox", -1.0, -1.0, -1.0, 2.0, 2.0, 2.0)
    helper_box.OpenEMSSimulationBox = True
    helper_box.BoundaryXMin = "PEC"
    helper_box.BoundaryXMax = "PMC"
    helper_box.BoundaryYMin = "MUR"
    helper_box.BoundaryYMax = "PML_8"
    helper_box.BoundaryZMin = "PEC"
    helper_box.BoundaryZMax = "MUR"
    helper_box.BoundaryPMLCells = 12

    legacy_boundary = OpenEMSObj(
        "Bnd",
        "OpenEMS_Boundary",
        XMin="PML_8",
        XMax="PML_8",
        YMin="PML_8",
        YMax="PML_8",
        ZMin="PML_8",
        ZMax="PML_8",
        PMLCells=8,
    )

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            legacy_boundary,
            geo,
            helper_box,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    boundary = extracted["boundary"]

    assert boundary["XMin"] == "PEC"
    assert boundary["XMax"] == "PMC"
    assert boundary["YMin"] == "MUR"
    assert boundary["YMax"] == "PML_8"
    assert boundary["ZMin"] == "PEC"
    assert boundary["ZMax"] == "MUR"
    assert boundary["PMLCells"] == 12


def test_document_reader_falls_back_to_legacy_boundary_when_no_sim_box():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    legacy_boundary = OpenEMSObj(
        "Bnd",
        "OpenEMS_Boundary",
        XMin="MUR",
        XMax="PEC",
        YMin="PMC",
        YMax="PML_8",
        ZMin="PEC",
        ZMax="PML_8",
        PMLCells=9,
    )

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            legacy_boundary,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    boundary = extracted["boundary"]

    assert boundary["XMin"] == "MUR"
    assert boundary["XMax"] == "PEC"
    assert boundary["YMin"] == "PMC"
    assert boundary["YMax"] == "PML_8"
    assert boundary["ZMin"] == "PEC"
    assert boundary["ZMax"] == "PML_8"
    assert boundary["PMLCells"] == 9


