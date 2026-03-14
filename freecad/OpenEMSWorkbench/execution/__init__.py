from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import shlex

try:
	from validation import run_preflight, summarize_findings
except ImportError:
	from OpenEMSWorkbench.validation import run_preflight, summarize_findings

try:
	from validation.member_collection import collect_members
except ImportError:
	from OpenEMSWorkbench.validation.member_collection import collect_members

try:
	from exporter import export_analysis_run_ready
except ImportError:
	from OpenEMSWorkbench.exporter import export_analysis_run_ready

try:
	from exporter.document_reader import read_analysis_for_export
except ImportError:
	from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

try:
	from execution.process_runner import run_process_blocking
	from execution.runtime_discovery import discover_python_runtime, validate_python_runtime
except ImportError:
	from OpenEMSWorkbench.execution.process_runner import run_process_blocking
	from OpenEMSWorkbench.execution.runtime_discovery import (
		discover_python_runtime,
		validate_python_runtime,
	)

try:
	from utils.runtime_settings import get_saved_solver_executable, set_saved_solver_executable
except ImportError:
	from OpenEMSWorkbench.utils.runtime_settings import (
		get_saved_solver_executable,
		set_saved_solver_executable,
	)


@dataclass
class ExecutionResult:
	status: str
	message: str
	exit_code: int | None = None
	duration_seconds: float | None = None
	command: list[str] = field(default_factory=list)
	paths: dict[str, str] = field(default_factory=dict)
	preflight_summary: dict[str, int | bool] = field(default_factory=dict)
	findings: list = field(default_factory=list)


def preflight_gate(analysis):
	findings = run_preflight(analysis)
	summary = summarize_findings(findings)
	return summary["ok"], findings, summary


def _parse_arguments(arguments: str) -> list[str]:
	text = arguments.strip()
	if not text:
		return []
	return shlex.split(text, posix=False)


def _looks_like_openems_binary(executable: str) -> bool:
	name = os.path.basename(executable).lower().strip()
	return name in {"openems", "openems.exe"}


def _looks_like_python_runtime(executable: str) -> bool:
	name = os.path.basename(executable).lower().strip()
	return name.startswith("python")


def _read_text(path: str) -> str:
	try:
		if not path or not os.path.isfile(path):
			return ""
		return Path(path).read_text(encoding="utf-8", errors="replace")
	except Exception:
		return ""


def _detect_solver_setup_failure(stdout_log: str, stderr_log: str) -> str:
	blob = (_read_text(stdout_log) + "\n" + _read_text(stderr_log)).lower()
	patterns = [
		"setup failed",
		"error code:",
		"cartoperator::setupcsxgrid",
		"fatal error",
	]
	for token in patterns:
		if token in blob:
			return token
	return ""


def _primary_simulation(analysis):
	members = collect_members(analysis)
	return members.simulations[0] if members.simulations else None


def auto_configure_solver_runtime(analysis) -> tuple[bool, str]:
	simulation = _primary_simulation(analysis)
	if simulation is None:
		return False, "No Simulation object found in active analysis."

	configured = str(getattr(simulation, "SolverExecutable", "")).strip()
	if configured:
		return True, f"SolverExecutable already configured: {configured}"

	saved = str(get_saved_solver_executable() or "").strip()
	if saved:
		ok, message = validate_python_runtime(saved)
		if ok:
			simulation.SolverExecutable = saved
			return True, f"Using saved runtime configuration: {saved}"

	discovery = discover_python_runtime()
	if not discovery.ok:
		checked = " | ".join(discovery.checked[-3:]) if discovery.checked else ""
		suffix = f" Checked: {checked}" if checked else ""
		return False, f"{discovery.message}{suffix}"

	simulation.SolverExecutable = discovery.executable
	set_saved_solver_executable(discovery.executable)
	if hasattr(simulation, "SolverArguments"):
		simulation.SolverArguments = str(getattr(simulation, "SolverArguments", "") or "")
	return True, discovery.message


def validate_configured_solver_runtime(analysis) -> tuple[bool, str]:
	simulation = _primary_simulation(analysis)
	if simulation is None:
		return False, "No Simulation object found in active analysis."

	executable = str(getattr(simulation, "SolverExecutable", "")).strip()
	if not executable:
		return False, "SolverExecutable is empty."

	if _looks_like_openems_binary(executable):
		return (
			False,
			"SolverExecutable points to openEMS.exe. Current Phase 7 runner executes a Python script; "
			"please use a Python interpreter with openEMS/CSXCAD modules.",
		)

	return validate_python_runtime(executable)


def run_analysis(
	analysis,
	base_output_dir: str | Path,
	document_name: str,
	on_stdout_line=None,
	on_stderr_line=None,
) -> ExecutionResult:
	ok, findings, summary = preflight_gate(analysis)
	if not ok:
		return ExecutionResult(
			status="blocked",
			message="Run blocked by preflight errors.",
			preflight_summary=summary,
			findings=findings,
		)

	extracted = read_analysis_for_export(analysis)
	simulation = extracted.get("simulation", {})
	solver_executable = str(simulation.get("SolverExecutable") or "").strip()
	solver_arguments = str(simulation.get("SolverArguments") or "").strip()
	run_blocking = bool(simulation.get("RunBlocking", True))
	out_dir = str(simulation.get("OutputDirectory") or "").strip()

	if not run_blocking:
		return ExecutionResult(
			status="failed",
			message="Non-blocking run mode is not implemented yet.",
			preflight_summary=summary,
			findings=findings,
		)

	if not solver_executable:
		return ExecutionResult(
			status="failed",
			message="Simulation SolverExecutable is empty.",
			preflight_summary=summary,
			findings=findings,
		)

	runtime_ok, runtime_message = validate_configured_solver_runtime(analysis)
	if not runtime_ok:
		return ExecutionResult(
			status="failed",
			message=runtime_message,
			preflight_summary=summary,
			findings=findings,
		)

	run_output_dir = out_dir if out_dir else None

	try:
		export_result = export_analysis_run_ready(
			analysis,
			base_output_dir,
			document_name,
			run_output_dir=run_output_dir,
		)
	except Exception as exc:
		return ExecutionResult(
			status="failed",
			message=f"Failed to export run-ready artifacts: {exc}",
			preflight_summary=summary,
			findings=findings,
		)

	paths = export_result.get("paths", {})
	script_path = str(paths.get("script", ""))
	stdout_log = str(paths.get("stdout_log", ""))
	stderr_log = str(paths.get("stderr_log", ""))
	cwd = str(paths.get("root", ""))

	command = [solver_executable]
	if _looks_like_python_runtime(solver_executable):
		command.append("-u")
	command.extend(_parse_arguments(solver_arguments))
	command.append(script_path)

	run_env = dict(os.environ)
	if _looks_like_python_runtime(solver_executable):
		run_env["PYTHONUNBUFFERED"] = "1"
		run_env.setdefault("PYTHONIOENCODING", "utf-8")

	try:
		proc_result = run_process_blocking(
			command=command,
			cwd=cwd,
			stdout_log=stdout_log,
			stderr_log=stderr_log,
			env=run_env,
			on_stdout_line=on_stdout_line,
			on_stderr_line=on_stderr_line,
		)
	except Exception as exc:
		return ExecutionResult(
			status="failed",
			message=f"Failed to launch solver process: {exc}",
			command=command,
			paths={k: str(v) for k, v in paths.items()},
			preflight_summary=summary,
			findings=findings,
		)

	if proc_result.exit_code != 0:
		return ExecutionResult(
			status="failed",
			message="Solver process exited with non-zero status.",
			exit_code=proc_result.exit_code,
			duration_seconds=proc_result.duration_seconds,
			command=proc_result.command,
			paths={k: str(v) for k, v in paths.items()},
			preflight_summary=summary,
			findings=findings,
		)

	failure_token = _detect_solver_setup_failure(proc_result.stdout_log, proc_result.stderr_log)
	if failure_token:
		return ExecutionResult(
			status="failed",
			message=(
				"Solver reported a setup/runtime failure in logs "
				f"(detected token: '{failure_token}')."
			),
			exit_code=proc_result.exit_code,
			duration_seconds=proc_result.duration_seconds,
			command=proc_result.command,
			paths={k: str(v) for k, v in paths.items()},
			preflight_summary=summary,
			findings=findings,
		)

	return ExecutionResult(
		status="succeeded",
		message="Simulation run completed successfully.",
		exit_code=proc_result.exit_code,
		duration_seconds=proc_result.duration_seconds,
		command=proc_result.command,
		paths={k: str(v) for k, v in paths.items()},
		preflight_summary=summary,
		findings=findings,
	)


__all__ = [
	"ExecutionResult",
	"preflight_gate",
	"auto_configure_solver_runtime",
	"validate_configured_solver_runtime",
	"run_analysis",
]
