from __future__ import annotations

import math
from pathlib import Path

try:
    from utils.unit_contract import (
        coerce_delta_unit,
        detect_freecad_length_unit_name,
        mm_to_model_unit_scale,
    )
except ImportError:
    from OpenEMSWorkbench.utils.unit_contract import (
        coerce_delta_unit,
        detect_freecad_length_unit_name,
        mm_to_model_unit_scale,
    )


def _as_float(value, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _as_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _normalize_direction(value) -> tuple[str, bool]:
    direction = str(value or "+z").strip().lower()
    if direction in {"x", "y", "z"}:
        return direction, False
    if direction in {"+x", "+y", "+z"}:
        return direction[1], False
    if direction in {"-x", "-y", "-z"}:
        return direction[1], True
    return "z", False


def _as_float_list(values) -> list[float]:
    if not isinstance(values, (list, tuple)):
        return []
    result: list[float] = []
    for value in values:
        try:
            result.append(float(value))
        except Exception:
            continue
    return result


def _grid_lines_from_model(model) -> tuple[str, list[float], list[float], list[float], list[float], list[float], float]:
    grid = model.grid or {}
    sim = model.simulation or {}
    mesh_lines = model.mesh_lines or {}
    coordinate_system = str(mesh_lines.get("coordinate_system") or grid.get("CoordinateSystem") or "Cartesian")
    delta_unit = coerce_delta_unit(sim.get("DeltaUnit"))
    scale = mm_to_model_unit_scale(delta_unit)
    x = _as_float_list(mesh_lines.get("x"))
    y = _as_float_list(mesh_lines.get("y"))
    z = _as_float_list(mesh_lines.get("z"))
    radial = _as_float_list(mesh_lines.get("radial"))
    azimuth = _as_float_list(mesh_lines.get("azimuth"))
    if coordinate_system == "Cylindrical" and radial and z:
        r_axis = [round(value * scale, 9) for value in radial]
        a_axis = [round(value, 9) for value in azimuth]
        z_axis = [round(value * scale, 9) for value in z]
        return coordinate_system, [], [], z_axis, r_axis, a_axis, delta_unit
    if x and y and z:
        x_axis = [round(value * scale, 9) for value in x]
        y_axis = [round(value * scale, 9) for value in y]
        z_axis = [round(value * scale, 9) for value in z]
        return coordinate_system, x_axis, y_axis, z_axis, [], [], delta_unit

    raise ValueError(
        "Export model is missing mesh lines. Regenerate mesh from the active analysis before export."
    )


def _vec3(values, default: list[float]) -> list[float]:
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return [float(default[0]), float(default[1]), float(default[2])]
    return [
        _as_float(values[0], default[0]),
        _as_float(values[1], default[1]),
        _as_float(values[2], default[2]),
    ]


def _scale_vec3(values: list[float], scale: float) -> list[float]:
    return [round(float(values[0]) * scale, 12), round(float(values[1]) * scale, 12), round(float(values[2]) * scale, 12)]


def _safe_symbol(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "material"
    chars = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            chars.append(ch)
        else:
            chars.append("_")
    symbol = "".join(chars)
    if symbol and symbol[0].isdigit():
        symbol = f"m_{symbol}"
    return symbol or "material"


def _coax_center_from_detection(detection: dict) -> tuple[float, float, float]:
    inner = detection.get("inner") or {}
    outer = detection.get("outer") or {}
    inner_center = list(inner.get("center", []) or [])
    outer_center = list(outer.get("center", []) or [])

    if len(inner_center) == 3 and len(outer_center) == 3:
        return (
            _as_float(0.5 * (inner_center[0] + outer_center[0]), 0.0),
            _as_float(0.5 * (inner_center[1] + outer_center[1]), 0.0),
            _as_float(0.5 * (inner_center[2] + outer_center[2]), 0.0),
        )
    if len(inner_center) == 3:
        return (_as_float(inner_center[0], 0.0), _as_float(inner_center[1], 0.0), _as_float(inner_center[2], 0.0))
    if len(outer_center) == 3:
        return (_as_float(outer_center[0], 0.0), _as_float(outer_center[1], 0.0), _as_float(outer_center[2], 0.0))
    return (0.0, 0.0, 0.0)


def _waveguide_plane_coordinates(
    face_name: str,
    source_offset_cells: int,
    x_lines: list[float],
    y_lines: list[float],
    z_lines: list[float],
) -> tuple[float, float] | None:
    axis_values = {
        "XMin": x_lines,
        "XMax": x_lines,
        "YMin": y_lines,
        "YMax": y_lines,
        "ZMin": z_lines,
        "ZMax": z_lines,
    }.get(str(face_name or ""))
    if not axis_values or len(axis_values) < 2:
        return None

    source_offset = _as_int(source_offset_cells, 3)
    if str(face_name).endswith("Min"):
        source_index = min(max(2, source_offset), len(axis_values) - 1)
        reference_index = source_index + 1
    else:
        source_index = max(0, (len(axis_values) - 1) - max(2, source_offset))
        reference_index = source_index - 1

    if reference_index < 0 or reference_index >= len(axis_values):
        return None
    return (float(axis_values[source_index]), float(axis_values[reference_index]))


def _waveguide_start_stop_from_plane(
    *,
    face_name: str,
    plane_coordinate: float,
    simulation_box: dict,
    model_scale: float,
) -> tuple[list[float], list[float]] | None:
    try:
        xmin = _as_float(simulation_box.get("XMin"), 0.0) * model_scale
        xmax = _as_float(simulation_box.get("XMax"), 0.0) * model_scale
        ymin = _as_float(simulation_box.get("YMin"), 0.0) * model_scale
        ymax = _as_float(simulation_box.get("YMax"), 0.0) * model_scale
        zmin = _as_float(simulation_box.get("ZMin"), 0.0) * model_scale
        zmax = _as_float(simulation_box.get("ZMax"), 0.0) * model_scale
    except Exception:
        return None

    plane = float(plane_coordinate)
    face = str(face_name or "")
    if face in {"XMin", "XMax"}:
        return ([plane, ymin, zmin], [plane, ymax, zmax])
    if face in {"YMin", "YMax"}:
        return ([xmin, plane, zmin], [xmax, plane, zmax])
    if face in {"ZMin", "ZMax"}:
        return ([xmin, ymin, plane], [xmax, ymax, plane])
    return None


def _coax_tem_field_lines(
    port: dict,
    *,
    model_scale: float,
    x_lines: list[float],
    y_lines: list[float],
    z_lines: list[float],
    simulation_box: dict,
) -> list[str]:
    lines: list[str] = []

    if str(port.get("PortType", "")).strip() != "Waveguide":
        return lines

    inference = port.get("WaveguideCoaxInference") or {}
    detection = port.get("WaveguideFaceGeometry") or {}
    contract = port.get("WaveguidePlaneContract") or {}

    if str(inference.get("status", "")) != "supported":
        lines.append(
            f"# Waveguide port {port.get('name')}: TEM field export skipped (inference {inference.get('status', 'missing')})."
        )
        return lines

    axis = str(inference.get("axis", "") or "").strip().lower()
    if axis not in {"x", "y", "z"}:
        lines.append(f"# Waveguide port {port.get('name')}: TEM field export skipped (invalid axis '{axis}').")
        return lines

    r_in = _as_float(inference.get("r_in"), 0.0) * model_scale
    r_out = _as_float(inference.get("r_out"), 0.0) * model_scale
    z0 = _as_float(inference.get("z0_ohm"), 0.0)
    if r_in <= 0.0 or r_out <= r_in or z0 <= 0.0:
        lines.append(f"# Waveguide port {port.get('name')}: TEM field export skipped (invalid coax parameters).")
        return lines

    center_raw = _coax_center_from_detection(detection)
    center = (
        round(center_raw[0] * model_scale, 12),
        round(center_raw[1] * model_scale, 12),
        round(center_raw[2] * model_scale, 12),
    )

    selected_face = str(contract.get("selected_face", "") or port.get("SimulationBoxFace", ""))
    source_offset_cells = _as_int(contract.get("source_offset_cells", port.get("SourcePlaneOffsetCells", 3)), 3)
    planes = _waveguide_plane_coordinates(selected_face, source_offset_cells, x_lines, y_lines, z_lines)
    source_plane = planes[0] if planes is not None else None
    reference_plane = planes[1] if planes is not None else None

    raw_direction = str(port.get("PropagationDirection", "+z") or "+z")
    prop = raw_direction.strip().lower()
    sign = 1.0
    if prop.startswith("-"):
        sign = -1.0

    number = _as_int(port.get("PortNumber", 1), 1)
    fn_prefix = f"port_{number}_coax_tem"

    lines.append(f"# Waveguide TEM fields for port {number} ({port.get('name')})")
    lines.append(f"# Coax parameters: a={round(r_in, 12)}, b={round(r_out, 12)}, epsilon_r={_as_float(inference.get('dielectric_epsilon_r'), 1.0)}, Z0={z0}")
    lines.append(f"# Coax center: ({center[0]}, {center[1]}, {center[2]})")
    if source_plane is not None and reference_plane is not None:
        lines.append(
            f"# Three-plane contract: face={selected_face}, source_plane={source_plane}, reference_plane={reference_plane}"
        )
    else:
        lines.append(f"# Three-plane contract: face={selected_face}, source/reference plane unavailable from mesh")
    lines.append(f"{fn_prefix}_a = {round(r_in, 12)}")
    lines.append(f"{fn_prefix}_b = {round(r_out, 12)}")
    lines.append(f"{fn_prefix}_z0 = {z0}")
    lines.append(f"{fn_prefix}_ln_ba = math.log({fn_prefix}_b / {fn_prefix}_a)")
    lines.append(f"{fn_prefix}_cx = {center[0]}")
    lines.append(f"{fn_prefix}_cy = {center[1]}")
    lines.append(f"{fn_prefix}_cz = {center[2]}")
    lines.append(f"{fn_prefix}_prop_sign = {sign}")
    lines.append("")
    lines.append(f"def {fn_prefix}_E(x, y, z):")
    if axis == "z":
        lines.append(f"    dx = x - {fn_prefix}_cx")
        lines.append(f"    dy = y - {fn_prefix}_cy")
        lines.append("    rho = math.sqrt(dx * dx + dy * dy)")
    elif axis == "x":
        lines.append(f"    dy = y - {fn_prefix}_cy")
        lines.append(f"    dz = z - {fn_prefix}_cz")
        lines.append("    rho = math.sqrt(dy * dy + dz * dz)")
    else:
        lines.append(f"    dx = x - {fn_prefix}_cx")
        lines.append(f"    dz = z - {fn_prefix}_cz")
        lines.append("    rho = math.sqrt(dx * dx + dz * dz)")
    lines.append(f"    if rho <= {fn_prefix}_a or rho >= {fn_prefix}_b or rho == 0.0:")
    lines.append("        return (0.0, 0.0, 0.0)")
    lines.append(f"    e_mag = 1.0 / (rho * {fn_prefix}_ln_ba)")
    if axis == "z":
        lines.append("    return (e_mag * dx / rho, e_mag * dy / rho, 0.0)")
    elif axis == "x":
        lines.append("    return (0.0, e_mag * dy / rho, e_mag * dz / rho)")
    else:
        lines.append("    return (e_mag * dx / rho, 0.0, e_mag * dz / rho)")
    lines.append("")
    lines.append(f"def {fn_prefix}_H(x, y, z):")
    if axis == "z":
        lines.append(f"    dx = x - {fn_prefix}_cx")
        lines.append(f"    dy = y - {fn_prefix}_cy")
        lines.append("    rho = math.sqrt(dx * dx + dy * dy)")
    elif axis == "x":
        lines.append(f"    dy = y - {fn_prefix}_cy")
        lines.append(f"    dz = z - {fn_prefix}_cz")
        lines.append("    rho = math.sqrt(dy * dy + dz * dz)")
    else:
        lines.append(f"    dx = x - {fn_prefix}_cx")
        lines.append(f"    dz = z - {fn_prefix}_cz")
        lines.append("    rho = math.sqrt(dx * dx + dz * dz)")
    lines.append(f"    if rho <= {fn_prefix}_a or rho >= {fn_prefix}_b or rho == 0.0:")
    lines.append("        return (0.0, 0.0, 0.0)")
    lines.append(f"    h_mag = 1.0 / (2.0 * math.pi * {fn_prefix}_z0 * rho)")
    if axis == "z":
        lines.append(f"    s = {fn_prefix}_prop_sign")
        lines.append("    return (-s * h_mag * dy / rho, s * h_mag * dx / rho, 0.0)")
    elif axis == "x":
        lines.append(f"    s = {fn_prefix}_prop_sign")
        lines.append("    return (0.0, -s * h_mag * dz / rho, s * h_mag * dy / rho)")
    else:
        lines.append(f"    s = {fn_prefix}_prop_sign")
        lines.append("    return (s * h_mag * dz / rho, 0.0, -s * h_mag * dx / rho)")
    lines.append("")
    lines.append(f"port_{number}_waveguide_tem = {{")
    lines.append(f"    'number': {number},")
    lines.append(f"    'axis': '{axis}',")
    lines.append(f"    'selected_face': {selected_face!r},")
    if source_plane is not None and reference_plane is not None:
        lines.append(f"    'source_plane': {source_plane},")
        lines.append(f"    'reference_plane': {reference_plane},")
    lines.append(f"    'E_func': {fn_prefix}_E,")
    lines.append(f"    'H_func': {fn_prefix}_H,")
    lines.append("}")

    direction_axis, reverse = _normalize_direction(raw_direction)
    source_start_stop = None
    reference_start_stop = None
    if source_plane is not None:
        source_start_stop = _waveguide_start_stop_from_plane(
            face_name=selected_face,
            plane_coordinate=source_plane,
            simulation_box=simulation_box,
            model_scale=model_scale,
        )
    if reference_plane is not None:
        reference_start_stop = _waveguide_start_stop_from_plane(
            face_name=selected_face,
            plane_coordinate=reference_plane,
            simulation_box=simulation_box,
            model_scale=model_scale,
        )

    excite = 1.0 if bool(port.get("Excite", False)) else 0.0
    if source_start_stop is not None:
        start, stop = source_start_stop
        if reverse:
            start, stop = stop, start
        lines.append(
            f"port_{number}_waveguide = _add_waveguide_port(FDTD, {number}, {start}, {stop}, '{direction_axis}', {excite}, {fn_prefix}_E, {fn_prefix}_H)"
        )
    else:
        lines.append(
            f"# Waveguide port {number}: skipped AddWaveGuidePort export because source-plane region could not be resolved."
        )

    if reference_start_stop is not None:
        ref_start, ref_stop = reference_start_stop
        if reverse:
            ref_start, ref_stop = ref_stop, ref_start
        lines.append(f"port_{number}_waveguide_reference_start = {ref_start}")
        lines.append(f"port_{number}_waveguide_reference_stop = {ref_stop}")
    else:
        lines.append(
            f"# Waveguide port {number}: probing/reference plane region unavailable in current mesh export context."
        )
    lines.append("# Phase 6.9: TEM spatial field functions are exported for waveguide/coax ports.")
    return lines


def generate_openems_script(
    model,
    script_path: str | Path,
    runnable: bool = False,
    run_output_dir: str | Path | None = None,
) -> Path:
    path = Path(script_path)
    lines: list[str] = []
    if runnable:
        lines.append("# Auto-generated by OpenEMS FreeCAD Workbench (Phase 7 run-ready)")
    else:
        lines.append("# Auto-generated by OpenEMS FreeCAD Workbench (dry-run export)")
    lines.append("import os")
    lines.append("_openems_root = os.environ.get('OPENEMS_INSTALL_DIR', '').strip()")
    lines.append("if _openems_root and hasattr(os, 'add_dll_directory'):")
    lines.append("    os.add_dll_directory(_openems_root)")
    lines.append("import math")
    lines.append("import CSXCAD")
    lines.append("import openEMS")
    lines.append("from pathlib import Path")
    lines.append("")
    lines.append("CSX = CSXCAD.ContinuousStructure()")
    coordinate_system, x_lines, y_lines, z_lines, radial_lines, azimuth_lines, delta_unit = _grid_lines_from_model(model)
    model_unit_name = str((model.simulation or {}).get("FreeCADLengthUnitName") or "").strip()
    if not model_unit_name:
        model_unit_name = detect_freecad_length_unit_name()
    model_scale = mm_to_model_unit_scale(delta_unit)
    lines.append(
        f"# Unit contract: coordinates are exported in FreeCAD unit '{model_unit_name}' "
        f"with SetDeltaUnit={delta_unit} meter per unit."
    )
    lines.append("grid = CSX.GetGrid()")
    lines.append(f"grid.SetDeltaUnit({delta_unit})")
    if coordinate_system == "Cylindrical" and radial_lines and z_lines:
        lines.append(f"grid.AddLine('r', {radial_lines})")
        if azimuth_lines:
            lines.append(f"grid.AddLine('a', {azimuth_lines})")
        lines.append(f"grid.AddLine('z', {z_lines})")
    else:
        lines.append(f"grid.AddLine('x', {x_lines})")
        lines.append(f"grid.AddLine('y', {y_lines})")
        lines.append(f"grid.AddLine('z', {z_lines})")
    lines.append("")
    sim = model.simulation or {}
    nr_ts = _as_int(sim.get("NumberOfTimeSteps", 100000), 100000)
    end_criteria = _as_float(sim.get("EndCriteria", 1e-5), 1e-5)
    lines.append(f"FDTD = openEMS.openEMS(NrTS={nr_ts}, EndCriteria={end_criteria})")
    lines.append("FDTD.SetCSX(CSX)")
    excitation_type = str(sim.get("ExcitationType", "Gaussian") or "Gaussian")
    if excitation_type == "Gaussian":
        f0 = _as_float(sim.get("ExcitationF0", 1e9), 1e9)
        fc = _as_float(sim.get("ExcitationFc", 5e8), 5e8)
        lines.append(f"FDTD.SetGaussExcite({f0}, {fc})")
    else:
        lines.append(f"# Unsupported excitation type for Phase 9 MVP: {excitation_type}")
    lines.append("")

    if model.boundary:
        b = model.boundary
        lines.append(
            "FDTD.SetBoundaryCond(["
            f"'{b.get('XMin', 'PEC')}', '{b.get('XMax', 'PEC')}', "
            f"'{b.get('YMin', 'PEC')}', '{b.get('YMax', 'PEC')}', "
            f"'{b.get('ZMin', 'PEC')}', '{b.get('ZMax', 'PEC')}'])"
        )
    lines.append("")

    lines.append("# Materials")
    material_vars: dict[str, str] = {}
    for idx, mat in enumerate(sorted(model.materials, key=lambda item: str(item.get("name", "")))):
        mat_name = str(mat.get("name", f"Material_{idx + 1}") or f"Material_{idx + 1}")
        symbol = f"mat_{idx}_{_safe_symbol(mat_name)}"
        material_vars[mat_name] = symbol

        is_pec = bool(mat.get("IsPEC", False))
        if is_pec:
            lines.append(f"{symbol} = CSX.AddMetal({mat_name!r})")
        else:
            eps = _as_float(mat.get("EpsilonR", 1.0), 1.0)
            mu = _as_float(mat.get("MuR", 1.0), 1.0)
            kappa = _as_float(mat.get("Kappa", 0.0), 0.0)
            lines.append(f"{symbol} = CSX.AddMaterial({mat_name!r})")
            lines.append(
                f"{symbol}.SetMaterialProperty(epsilon={eps}, mue={mu}, kappa={kappa})"
            )
        lines.append(
            f"# MAT {mat_name}: eps={mat.get('EpsilonR')} mu={mat.get('MuR')} "
            f"kappa={mat.get('Kappa')} pec={mat.get('IsPEC')}"
        )
    lines.append("")

    lines.append("# Geometry mapping")
    primitive_geometries = [geo for geo in model.geometries if geo.primitive in {"box", "cylinder"}]

    if primitive_geometries:
        needs_unassigned = any(
            str(getattr(geo, "assigned_material_name", "") or "").strip() not in material_vars
            for geo in primitive_geometries
        )
        if needs_unassigned:
            lines.append("_phase33_unassigned_prop = CSX.AddMaterial('_phase33_unassigned')")
            lines.append("_phase33_unassigned_prop.SetMaterialProperty(epsilon=1.0, mue=1.0, kappa=0.0)")

    for geo in sorted(model.geometries, key=lambda item: item.object_name):
        if geo.primitive == "box":
            start = _scale_vec3(_vec3(geo.params.get("start"), [0.0, 0.0, 0.0]), model_scale)
            stop = _scale_vec3(_vec3(geo.params.get("stop"), [1.0, 1.0, 1.0]), model_scale)
            material_name = str(getattr(geo, "assigned_material_name", "") or "").strip()
            prop_var = material_vars.get(material_name, "_phase33_unassigned_prop")
            priority = _as_int(getattr(geo, "assignment_priority", 0), 0)
            lines.append(f"{prop_var}.AddBox({start}, {stop}, priority={priority})")
            lines.append(
                f"# BOX {geo.object_name}: start={start} stop={stop}"
            )
        elif geo.primitive == "cylinder":
            base = _scale_vec3(_vec3(geo.params.get("base"), [0.0, 0.0, 0.0]), model_scale)
            radius = round(_as_float(geo.params.get("radius"), 1.0) * model_scale, 12)
            height = round(_as_float(geo.params.get("height"), 1.0) * model_scale, 12)
            top = [base[0], base[1], base[2] + height]
            material_name = str(getattr(geo, "assigned_material_name", "") or "").strip()
            prop_var = material_vars.get(material_name, "_phase33_unassigned_prop")
            priority = _as_int(getattr(geo, "assignment_priority", 0), 0)
            lines.append(f"{prop_var}.AddCylinder({base}, {top}, {radius}, priority={priority})")
            lines.append(
                f"# CYLINDER {geo.object_name}: base={base} r={radius} h={height}"
            )
        elif geo.primitive == "polyhedron":
            lines.append(
                f"# POLYHEDRON {geo.object_name}: stl={geo.params['stl_path']}"
            )
    lines.append("")

    has_waveguide_port = any(str(port.get("PortType", "")).strip() == "Waveguide" for port in model.ports)
    if has_waveguide_port:
        lines.append("# Waveguide port adapter")
        lines.append("def _add_waveguide_port(fdtd, number, start, stop, direction, excite, e_func, h_func):")
        lines.append("    attempts = [")
        lines.append("        lambda: fdtd.AddWaveGuidePort(number, start, stop, direction, excite, e_func, h_func),")
        lines.append("        lambda: fdtd.AddWaveGuidePort(number, start, stop, direction, e_func, h_func, excite),")
        lines.append("        lambda: fdtd.AddWaveGuidePort(num=number, start=start, stop=stop, p_dir=direction, excite=excite, E_func=e_func, H_func=h_func),")
        lines.append("    ]")
        lines.append("    for call in attempts:")
        lines.append("        try:")
        lines.append("            return call()")
        lines.append("        except TypeError:")
        lines.append("            continue")
        lines.append("    raise RuntimeError('Unable to call AddWaveGuidePort with supported signatures for this openEMS Python build.')")
        lines.append("")

    lines.append("# Ports")
    for port in model.ports:
        lines.append(
            f"# PORT {port.get('name')}: type={port.get('PortType')} "
            f"num={port.get('PortNumber')} R={port.get('Resistance')}"
        )
        if str(port.get("PortType", "")).strip() == "Lumped":
            number = _as_int(port.get("PortNumber", 1), 1)
            resistance = _as_float(port.get("Resistance", 50.0), 50.0)
            excite = 1.0 if bool(port.get("Excite", False)) else 0.0
            direction, reverse = _normalize_direction(port.get("PropagationDirection"))
            start = [
                round(_as_float(port.get("PortStartX", 0.0), 0.0) * model_scale, 12),
                round(_as_float(port.get("PortStartY", 0.0), 0.0) * model_scale, 12),
                round(_as_float(port.get("PortStartZ", 0.0), 0.0) * model_scale, 12),
            ]
            stop = [
                round(_as_float(port.get("PortStopX", 1.0), 1.0) * model_scale, 12),
                round(_as_float(port.get("PortStopY", 0.0), 0.0) * model_scale, 12),
                round(_as_float(port.get("PortStopZ", 0.0), 0.0) * model_scale, 12),
            ]
            if reverse:
                start, stop = stop, start
            lines.append(
                f"port_{number} = FDTD.AddLumpedPort({number}, {resistance}, {start}, {stop}, '{direction}', {excite})"
            )
        elif str(port.get("PortType", "")).strip() == "Waveguide":
            for field_line in _coax_tem_field_lines(
                port,
                model_scale=model_scale,
                x_lines=x_lines,
                y_lines=y_lines,
                z_lines=z_lines,
                simulation_box=model.simulation_box or {},
            ):
                lines.append(field_line)
    lines.append("")

    lines.append("# Dump boxes")
    for dump in model.dumpboxes:
        lines.append(
            f"# DUMP {dump.get('name')}: type={dump.get('DumpType')} freq={dump.get('FrequencySpec')}"
        )
    lines.append("")

    if runnable:
        output_dir = Path(run_output_dir) if run_output_dir else Path("./run")
        lines.append(f"sim_path = Path({str(output_dir)!r})")
        lines.append("sim_path.mkdir(parents=True, exist_ok=True)")
        lines.append("FDTD.Run(str(sim_path), verbose=3)")
        lines.append("print(f'openEMS run completed: {sim_path}')")
    else:
        lines.append("# Dry-run export script generated successfully")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
