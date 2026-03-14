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
	from exporter import export_analysis_run_ready
except ImportError:
	from OpenEMSWorkbench.exporter import export_analysis_run_ready

try:
	from exporter.document_reader import read_analysis_for_export
except ImportError:
	from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

try:
	from execution.process_runner import run_process_blocking
except ImportError:
	from OpenEMSWorkbench.execution.process_runner import run_process_blocking


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


def run_analysis(
	analysis,
	base_output_dir: str | Path,
	document_name: str,
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

	if _looks_like_openems_binary(solver_executable):
		return ExecutionResult(
			status="failed",
			message=(
				"SolverExecutable points to openEMS.exe, but Phase 7 Run Simulation "
				"executes the generated Python script. Set SolverExecutable to a Python "
				"interpreter that has openEMS/CSXCAD Python modules installed."
			),
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

	command = [solver_executable, *_parse_arguments(solver_arguments), script_path]

	try:
		proc_result = run_process_blocking(
			command=command,
			cwd=cwd,
			stdout_log=stdout_log,
			stderr_log=stderr_log,
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


__all__ = ["ExecutionResult", "preflight_gate", "run_analysis"]
