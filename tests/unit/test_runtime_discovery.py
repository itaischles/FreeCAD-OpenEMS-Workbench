from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_discover_python_runtime_returns_success_when_probe_passes(monkeypatch):
    from OpenEMSWorkbench.execution import runtime_discovery

    monkeypatch.setattr(runtime_discovery, "_candidate_executables", lambda: ["C:/Python/python.exe"])
    monkeypatch.setattr(runtime_discovery, "_probe_python_runtime", lambda executable: (True, "ok"))

    result = runtime_discovery.discover_python_runtime()
    assert result.ok
    assert result.executable == "C:/Python/python.exe"


def test_validate_python_runtime_reports_failure(monkeypatch):
    from OpenEMSWorkbench.execution import runtime_discovery

    monkeypatch.setattr(runtime_discovery, "_probe_python_runtime", lambda executable: (False, "missing module"))
    ok, message = runtime_discovery.validate_python_runtime("C:/Python/python.exe")
    assert not ok
    assert "missing module" in message
