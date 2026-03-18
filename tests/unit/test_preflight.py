from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class Proxy:
    def __init__(self, proxy_type):
        self.TYPE = proxy_type


class Obj:
    def __init__(self, name, proxy_type, **attrs):
        self.Name = name
        self.Label = name
        self.Proxy = Proxy(proxy_type)
        for key, value in attrs.items():
            setattr(self, key, value)


class Analysis:
    def __init__(self, group):
        self.Group = group


class GeoObj:
    def __init__(self, name, **attrs):
        self.Name = name
        self.Label = name
        self.Shape = object()
        for key, value in attrs.items():
            setattr(self, key, value)


class BoundBox:
    def __init__(self, xmin, ymin, zmin, xmax, ymax, zmax):
        self.XMin = xmin
        self.YMin = ymin
        self.ZMin = zmin
        self.XMax = xmax
        self.YMax = ymax
        self.ZMax = zmax


class Shape:
    def __init__(self, bounds):
        self.BoundBox = BoundBox(*bounds)


class MeshStub:
    def __init__(self, x, y, z):
        self.coordinate_system = "cartesian"
        self.x = tuple(x)
        self.y = tuple(y)
        self.z = tuple(z)


def _minimal_valid_analysis():
    sim = Obj(
        "Simulation",
        "OpenEMS_Simulation",
        CoordinateSystem="Cartesian",
        OutputDirectory="",
        ExcitationType="Gaussian",
        ExcitationF0=1.0e9,
        ExcitationFc=5.0e8,
    )
    grid = Obj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian")
    mat = Obj("Material", "OpenEMS_Material")
    port = Obj(
        "Port1",
        "OpenEMS_Port",
        PortType="Lumped",
        PortNumber=1,
        Resistance=50.0,
        Excite=True,
        PropagationDirection="+z",
        PortStartX=0.0,
        PortStartY=0.0,
        PortStartZ=0.0,
        PortStopX=0.0,
        PortStopY=0.0,
        PortStopZ=1.0,
    )
    dump = Obj("Dump", "OpenEMS_DumpBox", FrequencySpec="1e9,2e9")
    return Analysis([sim, grid, mat, port, dump])


def _minimal_valid_waveguide_analysis():
    analysis = _minimal_valid_analysis()
    port = analysis.Group[3]
    port.PortType = "Waveguide"
    port.SimulationBoxFace = "ZMin"
    port.SourcePlaneOffsetCells = 3
    port.PropagationDirection = "+z"

    inner = GeoObj(
        "InnerConductor",
        TypeId="Part::Cylinder",
        Radius=1.0,
        Height=10.0,
        Shape=Shape(bounds=(-1.0, -1.0, 0.0, 1.0, 1.0, 10.0)),
    )
    dielectric = GeoObj(
        "Dielectric",
        TypeId="Part::FeaturePython",
        OuterRadius=3.0,
        InnerRadius=1.0,
        Height=10.0,
        Shape=Shape(bounds=(-3.0, -3.0, 0.0, 3.0, 3.0, 10.0)),
    )
    outer = GeoObj(
        "OuterConductor",
        TypeId="Part::FeaturePython",
        OuterRadius=4.0,
        InnerRadius=3.0,
        Height=10.0,
        Shape=Shape(bounds=(-4.0, -4.0, 0.0, 4.0, 4.0, 10.0)),
    )

    sim_box = GeoObj(
        "OpenEMSSimulationBox",
        OpenEMSSimulationBox=True,
        BoundaryXMin="PEC",
        BoundaryXMax="PEC",
        BoundaryYMin="PEC",
        BoundaryYMax="PEC",
        BoundaryZMin="PEC",
        BoundaryZMax="PEC",
    )

    inner_material = Obj(
        "InnerMaterial",
        "OpenEMS_Material",
        AssignedGeometry=[inner],
        IsPEC=True,
    )
    dielectric_material = Obj(
        "DielectricMaterial",
        "OpenEMS_Material",
        AssignedGeometry=[dielectric],
        EpsilonR=2.1,
    )
    outer_material = Obj(
        "OuterMaterial",
        "OpenEMS_Material",
        AssignedGeometry=[outer],
        IsPEC=True,
    )

    # Replace the single minimal material with explicit coax assignments.
    analysis.Group[2] = inner_material
    analysis.Group.extend([dielectric_material, outer_material, inner, dielectric, outer, sim_box])
    return analysis


def test_preflight_passes_minimal_valid_setup():
    from OpenEMSWorkbench.validation.preflight import run_preflight, summarize_findings

    findings = run_preflight(_minimal_valid_analysis())
    summary = summarize_findings(findings)
    assert summary["errors"] == 0


def test_preflight_detects_required_object_failures():
    from OpenEMSWorkbench.validation.preflight import run_preflight, summarize_findings

    analysis = Analysis([])
    findings = run_preflight(analysis)
    summary = summarize_findings(findings)
    assert summary["errors"] >= 3


def test_preflight_requires_exactly_one_grid_object():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    findings = run_preflight(analysis)
    assert not any(f.check_id == "required.grid_count" for f in findings)

    analysis_without_grid = _minimal_valid_analysis()
    analysis_without_grid.Group = [
        obj
        for obj in analysis_without_grid.Group
        if getattr(getattr(obj, "Proxy", None), "TYPE", "") != "OpenEMS_Grid"
    ]
    findings_without_grid = run_preflight(analysis_without_grid)
    assert any(f.check_id == "required.grid_count" for f in findings_without_grid)

    analysis_with_duplicate_grid = _minimal_valid_analysis()
    analysis_with_duplicate_grid.Group.append(
        Obj("Grid2", "OpenEMS_Grid", CoordinateSystem="Cartesian")
    )
    findings_with_duplicate_grid = run_preflight(analysis_with_duplicate_grid)
    assert any(f.check_id == "required.grid_count" for f in findings_with_duplicate_grid)


def test_preflight_warns_when_mesh_fields_are_placed_on_simulation():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    simulation = analysis.Group[0]
    simulation.MeshBaseStep = 0.5
    simulation.MeshMaxStep = 2.0

    findings = run_preflight(analysis)
    assert any(f.check_id == "mesh.ownership_simulation_fields" for f in findings)


def test_preflight_detects_duplicate_ports():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    analysis.Group.append(Obj("Port2", "OpenEMS_Port", PortNumber=1))
    findings = run_preflight(analysis)
    assert any(f.check_id == "port.unique_number" for f in findings)


def test_preflight_warns_when_solver_executable_missing():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    findings = run_preflight(analysis)
    assert any(f.check_id == "simulation.solver_executable_configured" for f in findings)


def test_preflight_warns_for_openems_exe_in_script_mode():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    simulation = analysis.Group[0]
    simulation.SolverExecutable = "C:/tools/openEMS.exe"
    findings = run_preflight(analysis)
    assert any(f.check_id == "simulation.solver_executable_script_mode" for f in findings)


def test_preflight_blocks_unsupported_port_type_in_mvp():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    port = analysis.Group[3]
    port.PortType = "PlaneWave"
    findings = run_preflight(analysis)
    assert any(f.check_id == "port.type_supported" for f in findings)


def test_preflight_accepts_supported_waveguide_port_configuration():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_waveguide_analysis()
    findings = run_preflight(analysis)
    assert not any(f.check_id == "port.waveguide_geometry_supported" for f in findings)
    assert not any(f.check_id == "port.waveguide_inference_supported" for f in findings)
    assert not any(f.check_id == "port.waveguide_boundary_type_valid" for f in findings)


def test_preflight_rejects_waveguide_when_geometry_not_supported():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_waveguide_analysis()
    # Keep only one cylinder-like candidate so coax geometry detection is unsupported.
    analysis.Group = [
        obj
        for obj in analysis.Group
        if getattr(obj, "Name", "") not in {"OuterConductor", "Dielectric"}
    ]

    findings = run_preflight(analysis)
    assert any(f.check_id == "port.waveguide_geometry_supported" for f in findings)


def test_preflight_allows_waveguide_on_absorbing_boundary_face():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_waveguide_analysis()
    sim_box = next(obj for obj in analysis.Group if bool(getattr(obj, "OpenEMSSimulationBox", False)))
    sim_box.BoundaryZMin = "PML_8"

    findings = run_preflight(analysis)
    assert not any(f.check_id == "port.waveguide_boundary_defined" for f in findings)


def test_preflight_rejects_waveguide_when_direction_is_not_inward_for_selected_face():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_waveguide_analysis()
    port = analysis.Group[3]
    port.SimulationBoxFace = "ZMin"
    port.PropagationDirection = "-z"

    findings = run_preflight(analysis)
    assert any(f.check_id == "port.waveguide_direction_inward" for f in findings)


def test_preflight_rejects_waveguide_when_source_offset_exceeds_mesh_cells(monkeypatch):
    from OpenEMSWorkbench.validation import preflight

    analysis = _minimal_valid_waveguide_analysis()
    port = analysis.Group[3]
    port.SourcePlaneOffsetCells = 4

    mesh = MeshStub(x=(0.0, 1.0, 2.0), y=(0.0, 1.0, 2.0), z=(0.0, 1.0, 2.0, 3.0, 4.0))
    monkeypatch.setattr(preflight, "build_mesh_for_analysis", lambda _analysis: (None, None, mesh))

    findings = preflight.run_preflight(analysis)
    assert any(f.check_id == "port.waveguide_source_plane_offset_safe" for f in findings)


def test_preflight_rejects_waveguide_when_reference_plane_is_unavailable(monkeypatch):
    from OpenEMSWorkbench.validation import preflight

    analysis = _minimal_valid_waveguide_analysis()
    port = analysis.Group[3]
    port.SourcePlaneOffsetCells = 9

    mesh = MeshStub(x=(0.0, 1.0, 2.0), y=(0.0, 1.0, 2.0), z=(0.0, 1.0, 2.0, 3.0, 4.0))
    monkeypatch.setattr(preflight, "build_mesh_for_analysis", lambda _analysis: (None, None, mesh))

    findings = preflight.run_preflight(analysis)
    assert any(f.check_id == "port.waveguide_source_plane_offset_safe" for f in findings)


def test_preflight_blocks_invalid_excitation_values():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    simulation = analysis.Group[0]
    simulation.ExcitationF0 = 0.0
    findings = run_preflight(analysis)
    assert any(f.check_id == "simulation.excitation_f0_positive" for f in findings)


def test_preflight_requires_single_excited_port():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    port = analysis.Group[3]
    port.Excite = False
    findings = run_preflight(analysis)
    assert any(f.check_id == "port.single_excitation_source" for f in findings)


def test_preflight_requires_span_on_excitation_axis():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    port = analysis.Group[3]
    port.PropagationDirection = "+z"
    port.PortStartZ = 0.0
    port.PortStopZ = 0.0
    port.PortStopX = 1.0
    findings = run_preflight(analysis)
    assert any(f.check_id == "port.region_excitation_axis_span" for f in findings)


def test_preflight_requires_material_assignment_for_geometry():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    analysis.Group.append(GeoObj("GeoA"))

    findings = run_preflight(analysis)
    assert any(f.check_id == "material.geometry_assigned" for f in findings)


def test_preflight_rejects_stale_material_assignment_links():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    stale = GeoObj("StaleGeo")
    material = analysis.Group[2]
    material.AssignedGeometry = [stale]

    findings = run_preflight(analysis)
    assert any(f.check_id == "material.assignment_link_valid" for f in findings)


def test_preflight_rejects_duplicate_geometry_assignment_across_materials():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    geometry = GeoObj("GeoA")
    analysis.Group.append(geometry)

    material_a = analysis.Group[2]
    material_a.AssignedGeometry = [geometry]

    material_b = Obj("Material2", "OpenEMS_Material", AssignedGeometry=[geometry])
    analysis.Group.append(material_b)

    findings = run_preflight(analysis)
    assert any(f.check_id == "material.geometry_unique_assignment" for f in findings)


def test_preflight_enforces_delta_unit_contract():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    simulation = analysis.Group[0]
    simulation.DeltaUnit = 1.0

    findings = run_preflight(analysis)
    assert any(f.check_id == "simulation.delta_unit_contract" for f in findings)


def test_preflight_warns_when_stl_fallback_runtime_is_not_configured():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    geometry = GeoObj("GeoComplex", TypeId="Part::Feature")
    analysis.Group.append(geometry)
    material = analysis.Group[2]
    material.AssignedGeometry = [geometry]

    findings = run_preflight(analysis)

    assert any(f.check_id == "simulation.stl_reader_runtime_unchecked" for f in findings)


def test_preflight_rejects_stl_fallback_when_runtime_lacks_reader(monkeypatch):
    from OpenEMSWorkbench.validation import preflight

    analysis = _minimal_valid_analysis()
    geometry = GeoObj("GeoComplex", TypeId="Part::Feature")
    analysis.Group.append(geometry)
    material = analysis.Group[2]
    material.AssignedGeometry = [geometry]
    simulation = analysis.Group[0]
    simulation.SolverExecutable = "C:/Python/python.exe"

    monkeypatch.setattr(
        preflight,
        "_inspect_runtime_for_stl_reader",
        lambda executable: type(
            "RuntimeResult",
            (),
            {"ok": True, "message": "STL reader: unavailable", "capabilities": {"stl_reader": False}},
        )(),
    )

    findings = preflight.run_preflight(analysis)

    assert any(f.check_id == "simulation.stl_reader_required" for f in findings)


def test_preflight_accepts_stl_fallback_when_runtime_has_reader(monkeypatch):
    from OpenEMSWorkbench.validation import preflight

    analysis = _minimal_valid_analysis()
    geometry = GeoObj("GeoComplex", TypeId="Part::Feature")
    analysis.Group.append(geometry)
    material = analysis.Group[2]
    material.AssignedGeometry = [geometry]
    simulation = analysis.Group[0]
    simulation.SolverExecutable = "C:/Python/python.exe"

    monkeypatch.setattr(
        preflight,
        "_inspect_runtime_for_stl_reader",
        lambda executable: type(
            "RuntimeResult",
            (),
            {"ok": True, "message": "STL reader: available", "capabilities": {"stl_reader": True}},
        )(),
    )

    findings = preflight.run_preflight(analysis)

    assert not any(f.check_id == "simulation.stl_reader_required" for f in findings)
    assert not any(f.check_id == "simulation.stl_reader_runtime_unchecked" for f in findings)
