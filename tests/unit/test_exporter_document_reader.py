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
    def __init__(self, bb, faces=None):
        self.BoundBox = bb
        self.Faces = list(faces or [])


class _CylinderSurface:
    def __init__(self, axis_name="z"):
        self.Axis = type("Axis", (), {
            "x": 1.0 if axis_name == "x" else 0.0,
            "y": 1.0 if axis_name == "y" else 0.0,
            "z": 1.0 if axis_name == "z" else 0.0,
        })()


class _CylinderFace:
    def __init__(self, axis_name="z"):
        self.Surface = _CylinderSurface(axis_name=axis_name)


class GeoObjWithBounds:
    def __init__(self, name, xmin, ymin, zmin, xmax, ymax, zmax):
        self.Name = name
        self.Label = name
        self.Shape = _ShapeWithBoundBox(_BoundBox(xmin, ymin, zmin, xmax, ymax, zmax))


class CylinderObjWithBounds(GeoObjWithBounds):
    def __init__(self, name, xmin, ymin, zmin, xmax, ymax, zmax, radius=1.0, height=1.0):
        super().__init__(name, xmin, ymin, zmin, xmax, ymax, zmax)
        self.Radius = radius
        self.Height = height


class BodyLikeCylinderObj(GeoObjWithBounds):
    def __init__(self, name, xmin, ymin, zmin, xmax, ymax, zmax, axis_name="z"):
        self.Name = name
        self.Label = name
        self.Shape = _ShapeWithBoundBox(
            _BoundBox(xmin, ymin, zmin, xmax, ymax, zmax),
            faces=[_CylinderFace(axis_name=axis_name)],
        )


class TubeObjWithBounds(GeoObjWithBounds):
    def __init__(self, name, xmin, ymin, zmin, xmax, ymax, zmax, inner_radius, outer_radius):
        super().__init__(name, xmin, ymin, zmin, xmax, ymax, zmax)
        self.InnerRadius = inner_radius
        self.OuterRadius = outer_radius
        self.Height = zmax - zmin


class GroupedGeometryObj:
    def __init__(self, name, children, xmin, ymin, zmin, xmax, ymax, zmax):
        self.Name = name
        self.Label = name
        self.Group = list(children)
        self.Shape = _ShapeWithBoundBox(_BoundBox(xmin, ymin, zmin, xmax, ymax, zmax))


class _PlacementBase:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z


class _Placement:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.Base = _PlacementBase(x=x, y=y, z=z)


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


def test_document_reader_ignores_legacy_boundary_when_no_sim_box():
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

    assert boundary == {}


def test_document_reader_migrates_legacy_boundary_values_to_simulation_box():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    geo = GeoObjWithBounds("GeoA", 0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
    helper_box = GeoObjWithBounds("OpenEMSSimulationBox", -1.0, -1.0, -1.0, 2.0, 2.0, 2.0)
    helper_box.OpenEMSSimulationBox = True

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
            geo,
            helper_box,
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


def test_document_reader_normalizes_delta_unit_to_unit_contract():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", DeltaUnit=1.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            OpenEMSObj("Bnd", "OpenEMS_Boundary"),
        ]
    )

    extracted = read_analysis_for_export(analysis)
    assert extracted["simulation"]["DeltaUnit"] == 1e-3
    assert extracted["simulation"]["FreeCADLengthUnitName"] == "mm"


def test_document_reader_detects_supported_waveguide_face_coax_geometry():
    import math

    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    # Two concentric cylinders crossing the ZMin simulation-box face (z=0).
    inner = CylinderObjWithBounds("InnerPin", 4.0, 4.0, 0.0, 6.0, 6.0, 8.0, radius=1.0, height=8.0)
    dielectric = CylinderObjWithBounds("Dielectric", 3.4, 3.4, 0.0, 6.6, 6.6, 8.0, radius=1.6, height=8.0)
    outer = CylinderObjWithBounds("OuterShield", 3.0, 3.0, 0.0, 7.0, 7.0, 8.0, radius=2.0, height=8.0)

    inner_mat = OpenEMSObj(
        "MatInner",
        "OpenEMS_Material",
        EpsilonR=1.0,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=True,
        AssignmentPriority=1,
        AssignedGeometry=[inner],
    )
    dielectric_mat = OpenEMSObj(
        "MatDielectric",
        "OpenEMS_Material",
        EpsilonR=2.2,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=False,
        AssignmentPriority=1,
        AssignedGeometry=[dielectric],
    )
    outer_mat = OpenEMSObj(
        "MatOuter",
        "OpenEMS_Material",
        EpsilonR=1.0,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=True,
        AssignmentPriority=1,
        AssignedGeometry=[outer],
    )

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            inner_mat,
            dielectric_mat,
            outer_mat,
            OpenEMSObj(
                "Port1",
                "OpenEMS_Port",
                PortType="Waveguide",
                PortNumber=1,
                SimulationBoxFace="ZMin",
                SourcePlaneOffsetCells=3,
            ),
            inner,
            dielectric,
            outer,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    port = extracted["ports"][0]

    detected = port.get("WaveguideFaceGeometry")
    assert detected is not None
    assert detected["status"] == "supported"
    assert detected["kind"] == "coax_axis_aligned"
    assert detected["selected_face"] == "ZMin"
    assert detected["axis"] == "z"
    assert detected["inner"]["geometry_name"] == "InnerPin"
    assert detected["outer"]["geometry_name"] == "OuterShield"

    inferred = port.get("WaveguideCoaxInference")
    assert inferred is not None
    assert inferred["status"] == "supported"
    assert inferred["axis"] == "z"
    assert inferred["r_in"] == 1.0
    assert inferred["r_out"] == 2.0
    assert inferred["dielectric_epsilon_r"] == 2.2
    assert math.isclose(inferred["z0_ohm"], 28.039184028017946, rel_tol=1e-12, abs_tol=0.0)
    assert inferred["inner_conductor_geometry"] == "InnerPin"
    assert inferred["outer_conductor_geometry"] == "OuterShield"
    assert inferred["dielectric_material_name"] == "MatDielectric"

    contract = port.get("WaveguidePlaneContract")
    assert contract is not None
    assert contract["selected_face"] == "ZMin"
    assert contract["source_offset_cells"] == 3
    assert contract["reference_offset_cells"] == 4
    assert contract["expected_inward_direction"] == "+z"


def test_document_reader_reports_unsupported_waveguide_face_geometry_when_not_enough_candidates():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    only_one = CylinderObjWithBounds("OnlyOne", 4.0, 4.0, 0.0, 6.0, 6.0, 8.0, radius=1.0, height=8.0)

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            OpenEMSObj(
                "Port1",
                "OpenEMS_Port",
                PortType="Waveguide",
                PortNumber=1,
                SimulationBoxFace="ZMin",
                SourcePlaneOffsetCells=3,
            ),
            only_one,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    port = extracted["ports"][0]

    detected = port.get("WaveguideFaceGeometry")
    assert detected is not None
    assert detected["status"] == "unsupported"
    assert detected["reason"] == "insufficient_cylinder_candidates"

    inferred = port.get("WaveguideCoaxInference")
    assert inferred is not None
    assert inferred["status"] == "unsupported"
    assert inferred["reason"] == "geometry_detection_not_supported"


def test_document_reader_reports_unsupported_waveguide_inference_without_dielectric_material():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    inner = CylinderObjWithBounds("InnerPin", 4.0, 4.0, 0.0, 6.0, 6.0, 8.0, radius=1.0, height=8.0)
    outer = CylinderObjWithBounds("OuterShield", 3.0, 3.0, 0.0, 7.0, 7.0, 8.0, radius=2.0, height=8.0)

    inner_mat = OpenEMSObj(
        "MatInner",
        "OpenEMS_Material",
        EpsilonR=1.0,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=True,
        AssignmentPriority=1,
        AssignedGeometry=[inner],
    )
    outer_mat = OpenEMSObj(
        "MatOuter",
        "OpenEMS_Material",
        EpsilonR=1.0,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=True,
        AssignmentPriority=1,
        AssignedGeometry=[outer],
    )

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            inner_mat,
            outer_mat,
            OpenEMSObj(
                "Port1",
                "OpenEMS_Port",
                PortType="Waveguide",
                PortNumber=1,
                SimulationBoxFace="ZMin",
                SourcePlaneOffsetCells=3,
            ),
            inner,
            outer,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    inferred = extracted["ports"][0].get("WaveguideCoaxInference")
    assert inferred is not None
    assert inferred["status"] == "unsupported"
    assert inferred["reason"] == "dielectric_material_not_found"


def test_document_reader_detects_body_like_cylindrical_geometry_on_selected_face():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    inner = BodyLikeCylinderObj("InnerPinBody", 4.0, 4.0, 0.0, 6.0, 6.0, 8.0, axis_name="z")
    outer = BodyLikeCylinderObj("OuterShieldBody", 3.0, 3.0, 0.0, 7.0, 7.0, 8.0, axis_name="z")

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            OpenEMSObj(
                "Port1",
                "OpenEMS_Port",
                PortType="Waveguide",
                PortNumber=1,
                SimulationBoxFace="ZMin",
                SourcePlaneOffsetCells=3,
            ),
            inner,
            outer,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    detected = extracted["ports"][0].get("WaveguideFaceGeometry")

    assert detected is not None
    assert detected["status"] == "supported"
    assert detected["inner"]["geometry_name"] == "InnerPinBody"
    assert detected["outer"]["geometry_name"] == "OuterShieldBody"


def test_document_reader_detects_waveguide_geometry_inside_grouped_part_object():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    inner = BodyLikeCylinderObj("InnerPin", 4.0, 4.0, 0.0, 6.0, 6.0, 8.0, axis_name="z")
    dielectric = BodyLikeCylinderObj("DielectricTube", 3.5, 3.5, 0.0, 6.5, 6.5, 8.0, axis_name="z")
    outer = BodyLikeCylinderObj("OuterTube", 3.0, 3.0, 0.0, 7.0, 7.0, 8.0, axis_name="z")
    grouped_part = GroupedGeometryObj("CoaxAssembly", [outer, dielectric, inner], 3.0, 3.0, 0.0, 7.0, 7.0, 8.0)

    inner_material = OpenEMSObj(
        "InnerCond",
        "OpenEMS_Material",
        IsPEC=True,
        AssignedGeometry=[inner],
    )
    dielectric_material = OpenEMSObj(
        "Dielectric",
        "OpenEMS_Material",
        EpsilonR=2.1,
        AssignedGeometry=[dielectric],
    )
    outer_material = OpenEMSObj(
        "OuterCond",
        "OpenEMS_Material",
        IsPEC=True,
        AssignedGeometry=[outer],
    )

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            inner_material,
            dielectric_material,
            outer_material,
            OpenEMSObj(
                "Port1",
                "OpenEMS_Port",
                PortType="Waveguide",
                PortNumber=1,
                SimulationBoxFace="ZMin",
                SourcePlaneOffsetCells=3,
            ),
            grouped_part,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    detected = extracted["ports"][0].get("WaveguideFaceGeometry")
    inferred = extracted["ports"][0].get("WaveguideCoaxInference")

    assert detected is not None
    assert detected["status"] == "supported"
    assert detected["inner"]["geometry_name"] == "InnerPin"
    assert detected["outer"]["geometry_name"] == "OuterTube"
    assert inferred is not None
    assert inferred["status"] == "supported"


def test_document_reader_detects_grouped_waveguide_geometry_with_part_placement_offset():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    inner = BodyLikeCylinderObj("InnerPinShifted", -1.0, -1.0, 0.0, 1.0, 1.0, 8.0, axis_name="z")
    dielectric = BodyLikeCylinderObj("DielectricShifted", -1.5, -1.5, 0.0, 1.5, 1.5, 8.0, axis_name="z")
    outer = BodyLikeCylinderObj("OuterTubeShifted", -2.0, -2.0, 0.0, 2.0, 2.0, 8.0, axis_name="z")
    grouped_part = GroupedGeometryObj("ShiftedCoaxAssembly", [outer, dielectric, inner], 8.0, 8.0, 0.0, 12.0, 12.0, 8.0)
    grouped_part.Placement = _Placement(x=10.0, y=10.0, z=0.0)

    inner_material = OpenEMSObj(
        "InnerCondShifted",
        "OpenEMS_Material",
        IsPEC=True,
        AssignedGeometry=[inner],
    )
    dielectric_material = OpenEMSObj(
        "DielectricShiftedMat",
        "OpenEMS_Material",
        EpsilonR=2.1,
        AssignedGeometry=[dielectric],
    )
    outer_material = OpenEMSObj(
        "OuterCondShifted",
        "OpenEMS_Material",
        IsPEC=True,
        AssignedGeometry=[outer],
    )

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            inner_material,
            dielectric_material,
            outer_material,
            OpenEMSObj(
                "Port1",
                "OpenEMS_Port",
                PortType="Waveguide",
                PortNumber=1,
                SimulationBoxFace="ZMin",
                SourcePlaneOffsetCells=3,
            ),
            grouped_part,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    detected = extracted["ports"][0].get("WaveguideFaceGeometry")

    assert detected is not None
    assert detected["status"] == "supported"
    assert detected["inner"]["geometry_name"] == "InnerPinShifted"
    assert detected["outer"]["geometry_name"] == "OuterTubeShifted"


def test_document_reader_prefers_tube_and_cylinder_radius_properties_for_cut_solids():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    inner = CylinderObjWithBounds("InnerPin", 4.1, 4.1, 0.0, 5.9, 5.9, 8.0, radius=1.0, height=8.0)
    dielectric = TubeObjWithBounds("DielectricTube", 3.3, 3.3, 0.0, 6.7, 6.7, 8.0, inner_radius=1.0, outer_radius=1.6)
    outer = TubeObjWithBounds("OuterTube", 2.8, 2.8, 0.0, 7.2, 7.2, 8.0, inner_radius=1.6, outer_radius=2.0)

    inner_mat = OpenEMSObj(
        "MatInner",
        "OpenEMS_Material",
        EpsilonR=1.0,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=True,
        AssignmentPriority=1,
        AssignedGeometry=[inner],
    )
    dielectric_mat = OpenEMSObj(
        "MatDielectric",
        "OpenEMS_Material",
        EpsilonR=2.2,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=False,
        AssignmentPriority=1,
        AssignedGeometry=[dielectric],
    )
    outer_mat = OpenEMSObj(
        "MatOuter",
        "OpenEMS_Material",
        EpsilonR=1.0,
        MuR=1.0,
        Kappa=0.0,
        IsPEC=True,
        AssignmentPriority=1,
        AssignedGeometry=[outer],
    )

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            inner_mat,
            dielectric_mat,
            outer_mat,
            OpenEMSObj(
                "Port1",
                "OpenEMS_Port",
                PortType="Waveguide",
                PortNumber=1,
                SimulationBoxFace="ZMin",
                SourcePlaneOffsetCells=3,
            ),
            inner,
            dielectric,
            outer,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    port = extracted["ports"][0]
    detected = port.get("WaveguideFaceGeometry")
    inferred = port.get("WaveguideCoaxInference")

    assert detected is not None
    assert detected["status"] == "supported"
    assert detected["inner"]["radius"] == 1.0
    assert detected["inner"]["radius_source"] == "cylinder_properties"
    assert detected["outer"]["radius"] == 2.0
    assert detected["outer"]["radius_source"] == "tube_properties"
    assert inferred is not None
    assert inferred["status"] == "supported"
    assert inferred["r_in"] == 1.0
    assert inferred["r_out"] == 2.0


def test_document_reader_detects_cut_solids_with_slightly_uneven_circular_bounds():
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

    inner = CylinderObjWithBounds(
        "Cylinder",
        -9.954719225730846,
        -9.988673391830078,
        0.0,
        10.0,
        9.98867339183008,
        100.0,
        radius=10.0,
        height=100.0,
    )
    outer = TubeObjWithBounds(
        "Tube",
        -54.89568308053743,
        -54.973914584235125,
        0.0,
        55.0,
        54.973914584235125,
        100.0,
        inner_radius=10.0,
        outer_radius=55.0,
    )
    dielectric = TubeObjWithBounds(
        "Tube001",
        -50.0,
        -49.90133642141359,
        0.0,
        50.0,
        49.901336421413575,
        100.0,
        inner_radius=10.0,
        outer_radius=50.0,
    )

    inner_mat = OpenEMSObj(
        "MatInner",
        "OpenEMS_Material",
        IsPEC=True,
        AssignedGeometry=[inner],
    )
    dielectric_mat = OpenEMSObj(
        "MatDielectric",
        "OpenEMS_Material",
        EpsilonR=2.2,
        AssignedGeometry=[dielectric],
    )
    outer_mat = OpenEMSObj(
        "MatOuter",
        "OpenEMS_Material",
        IsPEC=True,
        AssignedGeometry=[outer],
    )

    analysis = Analysis(
        [
            OpenEMSObj("Sim", "OpenEMS_Simulation", SimulationBoxMargin=0.0),
            OpenEMSObj("Grid", "OpenEMS_Grid"),
            inner_mat,
            dielectric_mat,
            outer_mat,
            OpenEMSObj(
                "Port1",
                "OpenEMS_Port",
                PortType="Waveguide",
                PortNumber=1,
                SimulationBoxFace="ZMin",
                SourcePlaneOffsetCells=3,
            ),
            inner,
            dielectric,
            outer,
        ]
    )

    extracted = read_analysis_for_export(analysis)
    port = extracted["ports"][0]
    detected = port.get("WaveguideFaceGeometry")
    inferred = port.get("WaveguideCoaxInference")

    assert detected is not None
    assert detected["status"] == "supported"
    assert detected["axis"] == "z"
    assert detected["inner"]["geometry_name"] == "Cylinder"
    assert detected["outer"]["geometry_name"] == "Tube"
    assert inferred is not None
    assert inferred["status"] == "supported"
    assert inferred["r_in"] == 10.0
    assert inferred["r_out"] == 55.0


