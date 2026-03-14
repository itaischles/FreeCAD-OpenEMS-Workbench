from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class _ProcessResultStub:
    def __init__(self, exit_code=0, duration=0.25):
        self.exit_code = exit_code
        self.command = ["solver", "script.py"]
        self.cwd = "C:/tmp"
        self.duration_seconds = duration
        self.stdout_log = "C:/tmp/stdout.log"
        self.stderr_log = "C:/tmp/stderr.log"


class _SimulationProxy:
    TYPE = "OpenEMS_Simulation"


class _SimulationStub:
    def __init__(self, executable=""):
        self.Proxy = _SimulationProxy()
        self.SolverExecutable = executable
        self.SolverArguments = ""


class _AnalysisStub:
    def __init__(self, simulation):
        self.Group = [simulation]


def test_run_analysis_blocks_on_preflight_errors(monkeypatch, tmp_path):
    from OpenEMSWorkbench import execution

    monkeypatch.setattr(
        execution,
        "preflight_gate",
        lambda analysis: (False, ["err"], {"ok": False, "errors": 1, "warnings": 0, "infos": 0}),
    )

    result = execution.run_analysis(object(), tmp_path, "Doc")
    assert result.status == "blocked"
    assert result.preflight_summary["errors"] == 1


def test_run_analysis_fails_when_solver_executable_missing(monkeypatch, tmp_path):
    from OpenEMSWorkbench import execution

    monkeypatch.setattr(
        execution,
        "preflight_gate",
        lambda analysis: (True, [], {"ok": True, "errors": 0, "warnings": 0, "infos": 0}),
    )
    monkeypatch.setattr(
        execution,
        "read_analysis_for_export",
        lambda analysis: {"simulation": {"SolverExecutable": "", "RunBlocking": True, "OutputDirectory": ""}},
    )

    result = execution.run_analysis(object(), tmp_path, "Doc")
    assert result.status == "failed"
    assert "SolverExecutable" in result.message


def test_run_analysis_fails_for_openems_binary_in_python_script_mode(monkeypatch, tmp_path):
    from OpenEMSWorkbench import execution

    simulation = _SimulationStub(executable="C:/tools/openEMS.exe")
    analysis = _AnalysisStub(simulation)

    monkeypatch.setattr(
        execution,
        "preflight_gate",
        lambda analysis: (True, [], {"ok": True, "errors": 0, "warnings": 0, "infos": 0}),
    )
    monkeypatch.setattr(
        execution,
        "read_analysis_for_export",
        lambda _analysis: {
            "simulation": {
                "SolverExecutable": "C:/tools/openEMS.exe",
                "RunBlocking": True,
                "OutputDirectory": "",
            }
        },
    )

    result = execution.run_analysis(analysis, tmp_path, "Doc")
    assert result.status == "failed"
    assert "openEMS.exe" in result.message


def test_run_analysis_succeeds_with_mocked_runner(monkeypatch, tmp_path):
    from OpenEMSWorkbench import execution

    monkeypatch.setattr(
        execution,
        "validate_configured_solver_runtime",
        lambda analysis: (True, "ok"),
    )

    monkeypatch.setattr(
        execution,
        "preflight_gate",
        lambda analysis: (True, [], {"ok": True, "errors": 0, "warnings": 0, "infos": 0}),
    )
    monkeypatch.setattr(
        execution,
        "read_analysis_for_export",
        lambda analysis: {
            "simulation": {
                "SolverExecutable": "solver.exe",
                "SolverArguments": "--flag",
                "RunBlocking": True,
                "OutputDirectory": "",
            }
        },
    )
    monkeypatch.setattr(
        execution,
        "export_analysis_run_ready",
        lambda analysis, base_output_dir, document_name, run_output_dir=None: {
            "paths": {
                "root": str(tmp_path / "root"),
                "script": str(tmp_path / "root" / "openems_export.py"),
                "stdout_log": str(tmp_path / "root" / "logs" / "stdout.log"),
                "stderr_log": str(tmp_path / "root" / "logs" / "stderr.log"),
            }
        },
    )
    monkeypatch.setattr(execution, "run_process_blocking", lambda **kwargs: _ProcessResultStub(exit_code=0))

    result = execution.run_analysis(object(), tmp_path, "Doc")
    assert result.status == "succeeded"
    assert result.exit_code == 0


def test_run_analysis_reports_solver_nonzero_exit(monkeypatch, tmp_path):
    from OpenEMSWorkbench import execution

    monkeypatch.setattr(
        execution,
        "validate_configured_solver_runtime",
        lambda analysis: (True, "ok"),
    )

    monkeypatch.setattr(
        execution,
        "preflight_gate",
        lambda analysis: (True, [], {"ok": True, "errors": 0, "warnings": 0, "infos": 0}),
    )
    monkeypatch.setattr(
        execution,
        "read_analysis_for_export",
        lambda analysis: {
            "simulation": {
                "SolverExecutable": "solver.exe",
                "SolverArguments": "",
                "RunBlocking": True,
                "OutputDirectory": "",
            }
        },
    )
    monkeypatch.setattr(
        execution,
        "export_analysis_run_ready",
        lambda analysis, base_output_dir, document_name, run_output_dir=None: {
            "paths": {
                "root": str(tmp_path / "root"),
                "script": str(tmp_path / "root" / "openems_export.py"),
                "stdout_log": str(tmp_path / "root" / "logs" / "stdout.log"),
                "stderr_log": str(tmp_path / "root" / "logs" / "stderr.log"),
            }
        },
    )
    monkeypatch.setattr(execution, "run_process_blocking", lambda **kwargs: _ProcessResultStub(exit_code=3))

    result = execution.run_analysis(object(), tmp_path, "Doc")
    assert result.status == "failed"
    assert result.exit_code == 3


def test_auto_configure_solver_runtime_sets_detected_python(monkeypatch):
    from OpenEMSWorkbench import execution

    simulation = _SimulationStub(executable="")
    analysis = _AnalysisStub(simulation)

    monkeypatch.setattr(
        execution,
        "discover_python_runtime",
        lambda: type("R", (), {"ok": True, "executable": "C:/Python/python.exe", "message": "Detected Python runtime with openEMS modules: C:/Python/python.exe", "checked": []})(),
    )

    ok, message = execution.auto_configure_solver_runtime(analysis)
    assert ok
    assert "Detected Python runtime" in message
    assert simulation.SolverExecutable == "C:/Python/python.exe"


def test_auto_configure_solver_runtime_uses_saved_preference(monkeypatch):
    from OpenEMSWorkbench import execution

    simulation = _SimulationStub(executable="")
    analysis = _AnalysisStub(simulation)

    monkeypatch.setattr(execution, "get_saved_solver_executable", lambda: "C:/Saved/python.exe")
    monkeypatch.setattr(
        execution,
        "validate_python_runtime",
        lambda executable: (True, "ok"),
    )

    ok, message = execution.auto_configure_solver_runtime(analysis)
    assert ok
    assert "Using saved runtime configuration" in message
    assert simulation.SolverExecutable == "C:/Saved/python.exe"


def test_validate_configured_solver_runtime_rejects_openems_binary():
    from OpenEMSWorkbench import execution

    simulation = _SimulationStub(executable="C:/tools/openEMS.exe")
    analysis = _AnalysisStub(simulation)

    ok, message = execution.validate_configured_solver_runtime(analysis)
    assert not ok
    assert "openEMS.exe" in message


def test_run_analysis_adds_unbuffered_flag_for_python(monkeypatch, tmp_path):
    from OpenEMSWorkbench import execution

    seen: dict = {}

    monkeypatch.setattr(
        execution,
        "validate_configured_solver_runtime",
        lambda analysis: (True, "ok"),
    )
    monkeypatch.setattr(
        execution,
        "preflight_gate",
        lambda analysis: (True, [], {"ok": True, "errors": 0, "warnings": 0, "infos": 0}),
    )
    monkeypatch.setattr(
        execution,
        "read_analysis_for_export",
        lambda analysis: {
            "simulation": {
                "SolverExecutable": "python.exe",
                "SolverArguments": "",
                "RunBlocking": True,
                "OutputDirectory": "",
            }
        },
    )
    monkeypatch.setattr(
        execution,
        "export_analysis_run_ready",
        lambda analysis, base_output_dir, document_name, run_output_dir=None: {
            "paths": {
                "root": str(tmp_path / "root"),
                "script": str(tmp_path / "root" / "openems_export.py"),
                "stdout_log": str(tmp_path / "root" / "logs" / "stdout.log"),
                "stderr_log": str(tmp_path / "root" / "logs" / "stderr.log"),
            }
        },
    )

    def _runner(**kwargs):
        seen.update(kwargs)
        return _ProcessResultStub(exit_code=0)

    monkeypatch.setattr(execution, "run_process_blocking", _runner)
    monkeypatch.setattr(execution, "_detect_solver_setup_failure", lambda *_: "")

    result = execution.run_analysis(object(), tmp_path, "Doc")
    assert result.status == "succeeded"
    assert "-u" in seen["command"]
    assert seen["env"]["PYTHONUNBUFFERED"] == "1"


def test_run_analysis_fails_when_logs_report_setup_failure(monkeypatch, tmp_path):
    from OpenEMSWorkbench import execution

    monkeypatch.setattr(
        execution,
        "validate_configured_solver_runtime",
        lambda analysis: (True, "ok"),
    )
    monkeypatch.setattr(
        execution,
        "preflight_gate",
        lambda analysis: (True, [], {"ok": True, "errors": 0, "warnings": 0, "infos": 0}),
    )
    monkeypatch.setattr(
        execution,
        "read_analysis_for_export",
        lambda analysis: {
            "simulation": {
                "SolverExecutable": "solver.exe",
                "SolverArguments": "",
                "RunBlocking": True,
                "OutputDirectory": "",
            }
        },
    )
    monkeypatch.setattr(
        execution,
        "export_analysis_run_ready",
        lambda analysis, base_output_dir, document_name, run_output_dir=None: {
            "paths": {
                "root": str(tmp_path / "root"),
                "script": str(tmp_path / "root" / "openems_export.py"),
                "stdout_log": str(tmp_path / "root" / "logs" / "stdout.log"),
                "stderr_log": str(tmp_path / "root" / "logs" / "stderr.log"),
            }
        },
    )
    monkeypatch.setattr(execution, "run_process_blocking", lambda **kwargs: _ProcessResultStub(exit_code=0))
    monkeypatch.setattr(execution, "_detect_solver_setup_failure", lambda *_: "setup failed")

    result = execution.run_analysis(object(), tmp_path, "Doc")
    assert result.status == "failed"
    assert "setup/runtime failure" in result.message
