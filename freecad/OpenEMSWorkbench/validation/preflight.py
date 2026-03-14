from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

try:
    from validation.member_collection import collect_members
except ImportError:
    from OpenEMSWorkbench.validation.member_collection import collect_members


@dataclass
class PreflightFinding:
    severity: str
    check_id: str
    message: str
    object_name: str = ""


def _finding(severity: str, check_id: str, message: str, obj: Any = None) -> PreflightFinding:
    return PreflightFinding(
        severity=severity,
        check_id=check_id,
        message=message,
        object_name=getattr(obj, "Name", "") if obj is not None else "",
    )


def _check_required_counts(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []

    if len(members.simulations) != 1:
        findings.append(
            _finding(
                "error",
                "required.simulation_count",
                f"Analysis must contain exactly one Simulation object, found {len(members.simulations)}.",
            )
        )
    if len(members.grids) != 1:
        findings.append(
            _finding(
                "error",
                "required.grid_count",
                f"Analysis must contain exactly one Grid object, found {len(members.grids)}.",
            )
        )
    if len(members.materials) < 1:
        findings.append(
            _finding(
                "error",
                "required.material_count",
                "Analysis must contain at least one Material object.",
            )
        )
    if len(members.boundaries) != 1:
        findings.append(
            _finding(
                "error",
                "required.boundary_count",
                f"Analysis must contain exactly one Boundary object, found {len(members.boundaries)}.",
            )
        )

    return findings


def _check_port_numbers(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    used = {}
    for port in members.ports:
        number = int(getattr(port, "PortNumber", -1))
        if number in used:
            findings.append(
                _finding(
                    "error",
                    "port.unique_number",
                    f"Duplicate port number {number} found.",
                    port,
                )
            )
        else:
            used[number] = port
    return findings


def _check_coordinate_system(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    if not members.simulations or not members.grids:
        return findings

    sim = members.simulations[0]
    grid = members.grids[0]
    sim_cs = str(getattr(sim, "CoordinateSystem", ""))
    grid_cs = str(getattr(grid, "CoordinateSystem", ""))
    if sim_cs and grid_cs and sim_cs != grid_cs:
        findings.append(
            _finding(
                "error",
                "grid.coordinate_system_consistency",
                f"Simulation coordinate system '{sim_cs}' does not match grid coordinate system '{grid_cs}'.",
                grid,
            )
        )
    return findings


def _check_dumpbox_frequency(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    for dump in members.dumpboxes:
        spec = str(getattr(dump, "FrequencySpec", "")).strip()
        if not spec:
            continue
        parts = [p.strip() for p in spec.split(",") if p.strip()]
        try:
            _ = [float(p) for p in parts]
        except ValueError:
            findings.append(
                _finding(
                    "warning",
                    "dumpbox.frequency_spec_format",
                    f"FrequencySpec '{spec}' is not a comma-separated numeric list.",
                    dump,
                )
            )
    return findings


def _check_output_directory(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    if not members.simulations:
        return findings

    sim = members.simulations[0]
    out_dir = str(getattr(sim, "OutputDirectory", "")).strip()
    if not out_dir:
        return findings

    if not os.path.isdir(out_dir):
        findings.append(
            _finding(
                "warning",
                "simulation.output_directory_exists",
                f"Output directory does not exist: {out_dir}",
                sim,
            )
        )
        return findings

    if not os.access(out_dir, os.W_OK):
        findings.append(
            _finding(
                "warning",
                "simulation.output_directory_writable",
                f"Output directory is not writable: {out_dir}",
                sim,
            )
        )

    return findings


def _check_solver_configuration(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    if not members.simulations:
        return findings

    sim = members.simulations[0]
    executable = str(getattr(sim, "SolverExecutable", "")).strip()
    if not executable:
        findings.append(
            _finding(
                "warning",
                "simulation.solver_executable_configured",
                "SolverExecutable is empty. Run Simulation command will fail until configured.",
                sim,
            )
        )
    else:
        name = os.path.basename(executable).lower()
        if name in {"openems", "openems.exe"}:
            findings.append(
                _finding(
                    "warning",
                    "simulation.solver_executable_script_mode",
                    "Phase 7 Run Simulation executes Python scripts. Use a Python interpreter with openEMS modules instead of openEMS.exe.",
                    sim,
                )
            )
    return findings


def run_preflight(analysis: Any) -> list[PreflightFinding]:
    if analysis is None:
        return [
            _finding(
                "error",
                "analysis.exists",
                "No active OpenEMS analysis found.",
            )
        ]

    members = collect_members(analysis)
    findings: list[PreflightFinding] = []
    findings.extend(_check_required_counts(members))
    findings.extend(_check_port_numbers(members))
    findings.extend(_check_coordinate_system(members))
    findings.extend(_check_dumpbox_frequency(members))
    findings.extend(_check_output_directory(members))
    findings.extend(_check_solver_configuration(members))

    for unknown in members.unknown:
        findings.append(
            _finding(
                "info",
                "analysis.unknown_member",
                f"Unknown object in analysis group: {getattr(unknown, 'Label', unknown.Name)}",
                unknown,
            )
        )

    return findings


def summarize_findings(findings: list[PreflightFinding]) -> dict[str, int | bool]:
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    infos = sum(1 for f in findings if f.severity == "info")
    return {
        "errors": errors,
        "warnings": warnings,
        "infos": infos,
        "ok": errors == 0,
    }


def format_findings(findings: list[PreflightFinding]) -> list[str]:
    lines = []
    for finding in findings:
        target = f" [{finding.object_name}]" if finding.object_name else ""
        lines.append(
            f"{finding.severity.upper()} {finding.check_id}{target}: {finding.message}"
        )
    summary = summarize_findings(findings)
    lines.append(
        f"Preflight summary: errors={summary['errors']}, warnings={summary['warnings']}, infos={summary['infos']}"
    )
    return lines
