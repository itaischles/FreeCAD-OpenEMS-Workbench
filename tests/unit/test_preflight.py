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


def _minimal_valid_analysis():
    sim = Obj(
        "Simulation",
        "OpenEMS_Simulation",
        CoordinateSystem="Cartesian",
        OutputDirectory="",
    )
    grid = Obj("Grid", "OpenEMS_Grid", CoordinateSystem="Cartesian")
    mat = Obj("Material", "OpenEMS_Material")
    bnd = Obj("Boundary", "OpenEMS_Boundary")
    port = Obj("Port1", "OpenEMS_Port", PortNumber=1)
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
