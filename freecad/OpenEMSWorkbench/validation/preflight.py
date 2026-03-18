from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

try:
    from validation.member_collection import collect_members
except ImportError:
    from OpenEMSWorkbench.validation.member_collection import collect_members

try:
    from utils.unit_contract import (
        DEFAULT_LENGTH_UNIT_NAME,
        canonical_delta_unit_meters,
        is_supported_delta_unit,
    )
except ImportError:
    from OpenEMSWorkbench.utils.unit_contract import (
        DEFAULT_LENGTH_UNIT_NAME,
        canonical_delta_unit_meters,
        is_supported_delta_unit,
    )

try:
    from meshing import build_mesh_for_analysis
except ImportError:
    from OpenEMSWorkbench.meshing import build_mesh_for_analysis


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
                (
                    "Analysis must contain exactly one Grid object, "
                    f"found {len(members.grids)}. The Grid object owns mesh settings for the analysis."
                ),
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
    if len(members.ports) < 1:
        findings.append(
            _finding(
                "error",
                "required.port_count",
                "Analysis must contain at least one Port object.",
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
                (
                    f"Simulation coordinate system '{sim_cs}' does not match "
                    f"grid coordinate system '{grid_cs}'."
                ),
                grid,
            )
        )
    return findings


def _check_mesh_ownership_boundaries(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    if not members.simulations:
        return findings

    sim = members.simulations[0]
    misplaced_mesh_fields = [
        name
        for name in (
            "MeshBaseStep",
            "MeshMaxStep",
            "MeshGrowthRate",
            "MeshAutoSmooth",
            "MeshPreviewLineCap",
        )
        if hasattr(sim, name)
    ]
    if misplaced_mesh_fields:
        field_list = ", ".join(misplaced_mesh_fields)
        findings.append(
            _finding(
                "warning",
                "mesh.ownership_simulation_fields",
                (
                    "Mesh settings must be configured on the Grid object. "
                    f"Simulation contains mesh-like fields that are ignored: {field_list}."
                ),
                sim,
            )
        )

    return findings


def _check_legacy_boundary_objects(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    if not members.boundaries:
        return findings

    findings.append(
        _finding(
            "warning",
            "legacy.boundary_object_present",
            (
                f"Found {len(members.boundaries)} legacy Boundary object(s). "
                "Boundary settings are now sourced from the simulation box faces."
            ),
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


def _check_excitation(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    if not members.simulations:
        return findings

    sim = members.simulations[0]
    excitation_type = str(getattr(sim, "ExcitationType", "Gaussian")).strip()
    if excitation_type != "Gaussian":
        findings.append(
            _finding(
                "error",
                "simulation.excitation_type_supported",
                f"Excitation type '{excitation_type}' is not supported in Phase 9 MVP. Use Gaussian.",
                sim,
            )
        )

    try:
        f0 = float(getattr(sim, "ExcitationF0", 0.0))
    except Exception:
        f0 = 0.0
    try:
        fc = float(getattr(sim, "ExcitationFc", 0.0))
    except Exception:
        fc = 0.0

    if f0 <= 0.0:
        findings.append(
            _finding(
                "error",
                "simulation.excitation_f0_positive",
                "ExcitationF0 must be greater than 0 Hz.",
                sim,
            )
        )
    if fc <= 0.0:
        findings.append(
            _finding(
                "error",
                "simulation.excitation_fc_positive",
                "ExcitationFc must be greater than 0 Hz.",
                sim,
            )
        )

    return findings


def _check_unit_contract(members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    if not members.simulations:
        return findings

    sim = members.simulations[0]
    expected_delta_unit = canonical_delta_unit_meters()
    unit_name = DEFAULT_LENGTH_UNIT_NAME
    delta_unit = getattr(sim, "DeltaUnit", expected_delta_unit)
    if not is_supported_delta_unit(delta_unit, expected_delta_unit=expected_delta_unit):
        findings.append(
            _finding(
                "error",
                "simulation.delta_unit_contract",
                (
                    f"DeltaUnit must match current FreeCAD length unit '{unit_name}' "
                    f"({expected_delta_unit} m per unit) so openEMS reads the same units shown in FreeCAD."
                ),
                sim,
            )
        )

    return findings


def _check_port_configuration(analysis: Any, members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    valid_directions = {"x", "y", "z", "+x", "-x", "+y", "-y", "+z", "-z"}
    axis_index = {"x": 0, "y": 1, "z": 2}
    face_axis_map = {
        "XMin": "x",
        "XMax": "x",
        "YMin": "y",
        "YMax": "y",
        "ZMin": "z",
        "ZMax": "z",
    }
    excited_count = 0

    extracted = {}
    extracted_ports_by_name: dict[str, dict[str, Any]] = {}
    boundary_by_face: dict[str, Any] = {}
    if any(str(getattr(port, "PortType", "")).strip() == "Waveguide" for port in members.ports):
        try:
            try:
                from exporter.document_reader import read_analysis_for_export
            except ImportError:
                from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export

            extracted = read_analysis_for_export(analysis)
            extracted_ports_by_name = {
                str(item.get("name", "") or ""): item
                for item in list(extracted.get("ports", []) or [])
            }
            boundary_by_face = dict(extracted.get("boundary", {}) or {})
        except Exception as exc:
            findings.append(
                _finding(
                    "error",
                    "port.waveguide_export_context",
                    f"Failed to evaluate waveguide port context: {exc}",
                )
            )

    mesh = None
    if any(str(getattr(port, "PortType", "")).strip() == "Waveguide" for port in members.ports):
        try:
            _, _, mesh = build_mesh_for_analysis(analysis)
        except Exception:
            mesh = None

    for port in members.ports:
        port_type = str(getattr(port, "PortType", "Lumped")).strip()
        if port_type not in {"Lumped", "Waveguide"}:
            findings.append(
                _finding(
                    "error",
                    "port.type_supported",
                    f"Port type '{port_type}' is not supported in Phase 9 MVP. Use Lumped or Waveguide.",
                    port,
                )
            )

        try:
            resistance = float(getattr(port, "Resistance", 0.0))
        except Exception:
            resistance = 0.0
        if resistance <= 0.0:
            findings.append(
                _finding(
                    "error",
                    "port.resistance_positive",
                    "Port resistance must be greater than 0 Ohm.",
                    port,
                )
            )

        direction = str(getattr(port, "PropagationDirection", "+z")).strip().lower()
        if direction not in valid_directions:
            findings.append(
                _finding(
                    "error",
                    "port.direction_valid",
                    "PropagationDirection must be one of +x, -x, +y, -y, +z, -z.",
                    port,
                )
            )
            direction_axis = "z"
        else:
            direction_axis = direction[-1]

        if port_type == "Lumped":
            try:
                sx = float(getattr(port, "PortStartX", 0.0))
                sy = float(getattr(port, "PortStartY", 0.0))
                sz = float(getattr(port, "PortStartZ", 0.0))
                ex = float(getattr(port, "PortStopX", 0.0))
                ey = float(getattr(port, "PortStopY", 0.0))
                ez = float(getattr(port, "PortStopZ", 0.0))
            except Exception:
                findings.append(
                    _finding(
                        "error",
                        "port.region_numeric",
                        "Port start/stop coordinates must be numeric values.",
                        port,
                    )
                )
                continue

            start = [sx, sy, sz]
            stop = [ex, ey, ez]
            if sx == ex and sy == ey and sz == ez:
                findings.append(
                    _finding(
                        "error",
                        "port.region_non_degenerate",
                        "Port start and stop coordinates must define a non-degenerate region.",
                        port,
                    )
                )

            if start[axis_index[direction_axis]] == stop[axis_index[direction_axis]]:
                findings.append(
                    _finding(
                        "error",
                        "port.region_excitation_axis_span",
                        f"Port start/stop must differ along excitation direction '{direction_axis}'.",
                        port,
                    )
                )

        if port_type == "Waveguide":
            selected_face = str(getattr(port, "SimulationBoxFace", "") or "").strip()
            extracted_port = extracted_ports_by_name.get(str(getattr(port, "Name", "") or ""), {})
            detection = extracted_port.get("WaveguideFaceGeometry") or {}
            inference = extracted_port.get("WaveguideCoaxInference") or {}

            if str(detection.get("status", "")) != "supported":
                reason = str(detection.get("reason", "unknown") or "unknown")
                findings.append(
                    _finding(
                        "error",
                        "port.waveguide_geometry_supported",
                        f"Waveguide port requires supported coax geometry on face '{selected_face}' ({reason}).",
                        port,
                    )
                )

            if str(inference.get("status", "")) != "supported":
                reason = str(inference.get("reason", "unknown") or "unknown")
                findings.append(
                    _finding(
                        "error",
                        "port.waveguide_inference_supported",
                        f"Waveguide coax inference failed for face '{selected_face}' ({reason}).",
                        port,
                    )
                )

            face_boundary = str(boundary_by_face.get(selected_face, "") or "").strip()
            if not face_boundary:
                findings.append(
                    _finding(
                        "error",
                        "port.waveguide_boundary_defined",
                        f"Waveguide port face '{selected_face}' must have an explicit simulation-box boundary type.",
                        port,
                    )
                )

            offset_cells = int(getattr(port, "SourcePlaneOffsetCells", 0) or 0)
            if offset_cells < 2 or offset_cells > 9:
                findings.append(
                    _finding(
                        "error",
                        "port.waveguide_source_plane_offset_range",
                        "Waveguide source-plane offset must be between 2 and 9 mesh cells.",
                        port,
                    )
                )

            axis_name = face_axis_map.get(selected_face)
            axis_values = tuple(getattr(mesh, axis_name, ()) or ()) if mesh is not None and axis_name else ()
            if axis_name and len(axis_values) >= 2:
                max_safe_offset = len(axis_values) - 2
                if offset_cells > max_safe_offset:
                    findings.append(
                        _finding(
                            "error",
                            "port.waveguide_source_plane_offset_safe",
                            (
                                f"Waveguide source-plane offset {offset_cells} cells is too large for face '{selected_face}'. "
                                f"Maximum safe offset for current mesh is {max_safe_offset} cells."
                            ),
                            port,
                        )
                    )

        if bool(getattr(port, "Excite", False)):
            excited_count += 1

    if members.ports and excited_count != 1:
        findings.append(
            _finding(
                "error",
                "port.single_excitation_source",
                f"Exactly one excited port is required for Phase 9 MVP, found {excited_count}.",
            )
        )

    return findings


def _is_geometry_object(obj: Any) -> bool:
    if obj is None:
        return False
    proxy = getattr(obj, "Proxy", None)
    proxy_type = str(getattr(proxy, "TYPE", ""))
    if proxy_type.startswith("OpenEMS_"):
        return False
    return hasattr(obj, "Shape")


def _geometry_in_analysis(analysis: Any) -> list[Any]:
    geometry = []
    for obj in list(getattr(analysis, "Group", [])):
        if _is_geometry_object(obj):
            geometry.append(obj)
    return geometry


def _check_material_assignments(analysis: Any, members) -> list[PreflightFinding]:
    findings: list[PreflightFinding] = []
    geometry = _geometry_in_analysis(analysis)

    analysis_group = list(getattr(analysis, "Group", []))
    assignment_map: dict[str, list[Any]] = {}

    for material in members.materials:
        links = getattr(material, "AssignedGeometry", [])
        if not isinstance(links, (list, tuple)):
            continue

        names_in_material = set()
        for linked in links:
            linked_name = str(getattr(linked, "Name", "")).strip()
            if not linked_name or linked_name in names_in_material:
                continue
            names_in_material.add(linked_name)

            if linked not in analysis_group or not _is_geometry_object(linked):
                findings.append(
                    _finding(
                        "error",
                        "material.assignment_link_valid",
                        f"Material assignment contains stale or invalid linked object '{linked_name}'.",
                        material,
                    )
                )
                continue

            assignment_map.setdefault(linked_name, []).append(material)

    for obj in geometry:
        name = str(getattr(obj, "Name", "")).strip()
        assigned_materials = assignment_map.get(name, [])
        if len(assigned_materials) == 0:
            findings.append(
                _finding(
                    "error",
                    "material.geometry_assigned",
                    f"Geometry '{name}' must be assigned to exactly one material.",
                    obj,
                )
            )
        elif len(assigned_materials) > 1:
            material_names = ", ".join(
                str(getattr(item, "Name", "")) for item in assigned_materials
            )
            findings.append(
                _finding(
                    "error",
                    "material.geometry_unique_assignment",
                    f"Geometry '{name}' is assigned to multiple materials: {material_names}.",
                    obj,
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
    findings.extend(_check_legacy_boundary_objects(members))
    findings.extend(_check_port_numbers(members))
    findings.extend(_check_coordinate_system(members))
    findings.extend(_check_mesh_ownership_boundaries(members))
    findings.extend(_check_dumpbox_frequency(members))
    findings.extend(_check_output_directory(members))
    findings.extend(_check_solver_configuration(members))
    findings.extend(_check_unit_contract(members))
    findings.extend(_check_excitation(members))
    findings.extend(_check_port_configuration(analysis, members))
    findings.extend(_check_material_assignments(analysis, members))

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
