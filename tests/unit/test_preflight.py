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
    def __init__(self, name):
        self.Name = name
        self.Label = name
        self.Shape = object()


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
    bnd = Obj("Boundary", "OpenEMS_Boundary")
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
    return Analysis([sim, grid, mat, bnd, port, dump])


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


def test_preflight_blocks_non_lumped_port_type_in_mvp():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    port = analysis.Group[4]
    port.PortType = "Waveguide"
    findings = run_preflight(analysis)
    assert any(f.check_id == "port.type_supported" for f in findings)


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
    port = analysis.Group[4]
    port.Excite = False
    findings = run_preflight(analysis)
    assert any(f.check_id == "port.single_excitation_source" for f in findings)


def test_preflight_requires_span_on_excitation_axis():
    from OpenEMSWorkbench.validation.preflight import run_preflight

    analysis = _minimal_valid_analysis()
    port = analysis.Group[4]
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
