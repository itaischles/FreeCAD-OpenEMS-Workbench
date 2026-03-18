from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_discover_python_runtime_returns_success_when_probe_passes(monkeypatch):
    from OpenEMSWorkbench.execution import runtime_discovery

    monkeypatch.setattr(runtime_discovery, "_candidate_executables", lambda: ["C:/Python/python.exe"])
    monkeypatch.setattr(
        runtime_discovery,
        "inspect_python_runtime",
        lambda executable, timeout_seconds=20: runtime_discovery.RuntimeDiscoveryResult(
            ok=True,
            executable=executable,
            message="STL reader: available",
            capabilities={"stl_reader": True},
            details={"polyhedron_reader_class": "present", "stl_file_enum": "present"},
        ),
    )

    result = runtime_discovery.discover_python_runtime()
    assert result.ok
    assert result.executable == "C:/Python/python.exe"
    assert result.capabilities["stl_reader"] is True
    assert "STL reader: available" in result.message


def test_inspect_python_runtime_parses_stl_reader_capability(monkeypatch):
    from OpenEMSWorkbench.execution import runtime_discovery

    class Proc:
        returncode = 0
        stdout = (
            'OPENEMS_PYTHON_RUNTIME={"capabilities": {"stl_reader": true}, '
            '"details": {"polyhedron_reader_class": "present", "stl_file_enum": "present"}}\n'
        )
        stderr = ""

    monkeypatch.setattr(runtime_discovery.subprocess, "run", lambda *args, **kwargs: Proc())
    monkeypatch.setattr(runtime_discovery, "_resolve_openems_install_dir", lambda: r"C:\openEMS")

    result = runtime_discovery.inspect_python_runtime("C:/Python/python.exe")

    assert result.ok
    assert result.capabilities["stl_reader"] is True
    assert result.details["polyhedron_reader_class"] == "present"
    assert result.details["stl_file_enum"] == "present"


def test_validate_python_runtime_reports_failure(monkeypatch):
    from OpenEMSWorkbench.execution import runtime_discovery

    monkeypatch.setattr(
        runtime_discovery,
        "inspect_python_runtime",
        lambda executable, timeout_seconds=20: runtime_discovery.RuntimeDiscoveryResult(
            ok=False,
            executable=executable,
            message="missing module",
        ),
    )
    ok, message = runtime_discovery.validate_python_runtime("C:/Python/python.exe")
    assert not ok
    assert "missing module" in message


def test_validate_python_runtime_reports_stl_reader_status(monkeypatch):
    from OpenEMSWorkbench.execution import runtime_discovery

    monkeypatch.setattr(
        runtime_discovery,
        "inspect_python_runtime",
        lambda executable, timeout_seconds=20: runtime_discovery.RuntimeDiscoveryResult(
            ok=True,
            executable=executable,
            message="STL reader: unavailable",
            capabilities={"stl_reader": False},
            details={"polyhedron_reader_class": "present", "stl_file_enum": "missing"},
        ),
    )

    ok, message = runtime_discovery.validate_python_runtime("C:/Python/python.exe")

    assert ok
    assert "STL reader: unavailable" in message
