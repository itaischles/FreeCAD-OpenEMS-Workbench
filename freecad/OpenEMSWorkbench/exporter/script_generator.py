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


def _normalized_excitation_type(value: str) -> str:
    text = str(value or "Gaussian").strip().lower()
    if text in {"gaussian", "gauss", "gaussianpulse", "gaussian_pulse"}:
        return "Gaussian"
    if text in {"sinusoid", "sinusoidal", "sine"}:
        return "Sinusoid"
    if text in {"custom", "custom-expression", "custom_expression"}:
        return "Custom"
    return "Gaussian"


def _build_excitation_spec(sim: dict) -> dict:
    kind = _normalized_excitation_type(sim.get("ExcitationType", "Gaussian"))
    spec = {
        "type": kind,
        "f_max": _as_float(sim.get("ExcitationFMax", 0.0), 0.0),
        "f0": _as_float(sim.get("ExcitationF0", 1e9), 1e9),
        "fc": _as_float(sim.get("ExcitationFc", 5e8), 5e8),
        "sinusoid_amplitude": _as_float(sim.get("SinusoidAmplitude", 1.0), 1.0),
        "sinusoid_frequency": _as_float(sim.get("SinusoidFrequency", 1e9), 1e9),
        "sinusoid_phase_deg": _as_float(sim.get("SinusoidPhaseDeg", 0.0), 0.0),
        "custom_expression": str(sim.get("CustomExcitationExpression", "") or "").strip(),
    }
    return spec


def _emit_gaussian_excitation(lines: list[str], spec: dict) -> None:
    lines.append(f"FDTD.SetGaussExcite({spec['f0']}, {spec['fc']})")


def _emit_sinusoid_excitation(lines: list[str], spec: dict) -> None:
    lines.append(f"FDTD.SetSinusExcite({spec['sinusoid_frequency']})")
    lines.append(
        f"# Sinusoid parameters: amplitude={spec['sinusoid_amplitude']}, phase_deg={spec['sinusoid_phase_deg']}"
    )


def _emit_custom_excitation(lines: list[str], spec: dict) -> None:
    expression = str(spec.get("custom_expression", "") or "").strip()
    if not expression:
        expression = "0"
    lines.append(f"custom_excitation_expression = {expression!r}")
    lines.append("_set_custom_excite = getattr(FDTD, 'SetCustomExcite', None)")
    lines.append("if _set_custom_excite is None:")
    lines.append("    raise RuntimeError('Configured openEMS Python binding does not expose SetCustomExcite required for Custom excitation.')")
    lines.append("_custom_attempts = [")
    lines.append("    lambda: _set_custom_excite(custom_excitation_expression),")
    lines.append("    lambda: _set_custom_excite(custom_excitation_expression, 0),")
    lines.append("    lambda: _set_custom_excite(funcStr=custom_excitation_expression),")
    lines.append("    lambda: _set_custom_excite(funcStr=custom_excitation_expression, f0=0),")
    lines.append("]")
    lines.append("_custom_excite_ok = False")
    lines.append("for _custom_call in _custom_attempts:")
    lines.append("    try:")
    lines.append("        _custom_call()")
    lines.append("        _custom_excite_ok = True")
    lines.append("        break")
    lines.append("    except TypeError:")
    lines.append("        continue")
    lines.append("if not _custom_excite_ok:")
    lines.append("    raise RuntimeError('Unable to call SetCustomExcite with supported signatures for this openEMS Python build.')")


_EXCITATION_BACKENDS = {
    "Gaussian": _emit_gaussian_excitation,
    "Sinusoid": _emit_sinusoid_excitation,
    "Custom": _emit_custom_excitation,
}


def _emit_excitation(lines: list[str], sim: dict) -> None:
    spec = _build_excitation_spec(sim)
    lines.append(f"# Excitation backend: {spec['type']} (f_max={spec['f_max']})")
    backend = _EXCITATION_BACKENDS.get(spec["type"], _emit_gaussian_excitation)
    backend(lines, spec)


def _derive_run_limits(sim: dict) -> tuple[int, float]:
    default_nrts = 100000
    configured_nrts = _as_int(sim.get("NumberOfTimeSteps", default_nrts), default_nrts)
    computed_nrts = _as_int(sim.get("ComputedNumberOfTimeSteps", 0), 0)
    dt_sec = _as_float(sim.get("ComputedTimeStep", 0.0), 0.0)
    max_time_sec = _as_float(sim.get("MaxSimulationTime", 0.0), 0.0)

    derived_nrts = 0
    if max_time_sec > 0.0 and dt_sec > 0.0 and math.isfinite(max_time_sec) and math.isfinite(dt_sec):
        try:
            derived_nrts = int(math.ceil(max_time_sec / dt_sec))
        except Exception:
            derived_nrts = 0

    if derived_nrts > 0:
        nr_ts = derived_nrts
    elif computed_nrts > 0:
        nr_ts = computed_nrts
    elif configured_nrts > 0:
        nr_ts = configured_nrts
    else:
        nr_ts = default_nrts

    if max_time_sec <= 0.0 or not math.isfinite(max_time_sec):
        if dt_sec > 0.0 and math.isfinite(dt_sec):
            max_time_sec = float(nr_ts) * dt_sec
        else:
            max_time_sec = 0.0

    return int(max(1, nr_ts)), float(max_time_sec)


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


def _stl_path_for_geometry(geo) -> str:
    return str(
        getattr(getattr(geo, "stl_artifact", None), "path", "")
        or geo.params.get("stl_path", "")
    )


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


def _normalized_dump_type(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in {"efield", "e_field", "electric", "electricfield"}:
        return "EField"
    return "Unknown"


def _normalized_plane_axis(value: str) -> str:
    axis = str(value or "Z").strip().upper()
    if axis in {"X", "Y", "Z"}:
        return axis
    return "Z"


def _scaled_simulation_bounds(simulation_box: dict, model_scale: float) -> tuple[float, float, float, float, float, float] | None:
    required = ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax")
    if not all(key in simulation_box for key in required):
        return None
    xmin = _as_float(simulation_box.get("XMin"), 0.0) * model_scale
    xmax = _as_float(simulation_box.get("XMax"), 0.0) * model_scale
    ymin = _as_float(simulation_box.get("YMin"), 0.0) * model_scale
    ymax = _as_float(simulation_box.get("YMax"), 0.0) * model_scale
    zmin = _as_float(simulation_box.get("ZMin"), 0.0) * model_scale
    zmax = _as_float(simulation_box.get("ZMax"), 0.0) * model_scale
    return (xmin, xmax, ymin, ymax, zmin, zmax)


def _mesh_bounds(
    x_lines: list[float],
    y_lines: list[float],
    z_lines: list[float],
) -> tuple[float, float, float, float, float, float] | None:
    if len(x_lines) < 2 or len(y_lines) < 2 or len(z_lines) < 2:
        return None
    return (
        float(min(x_lines)),
        float(max(x_lines)),
        float(min(y_lines)),
        float(max(y_lines)),
        float(min(z_lines)),
        float(max(z_lines)),
    )


def _plane_start_stop_from_bounds(axis: str, bounds: tuple[float, float, float, float, float, float]) -> tuple[list[float], list[float]]:
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    if axis == "X":
        mid = round(0.5 * (xmin + xmax), 12)
        return ([mid, ymin, zmin], [mid, ymax, zmax])
    if axis == "Y":
        mid = round(0.5 * (ymin + ymax), 12)
        return ([xmin, mid, zmin], [xmax, mid, zmax])
    mid = round(0.5 * (zmin + zmax), 12)
    return ([xmin, ymin, mid], [xmax, ymax, mid])


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
    if axis == "z":
        lines.append(f"{fn_prefix}_E_expr = [")
        lines.append(f"    '((x-({fn_prefix}_cx))/(((x-({fn_prefix}_cx))**2 + (y-({fn_prefix}_cy))**2)*{fn_prefix}_ln_ba))',")
        lines.append(f"    '((y-({fn_prefix}_cy))/(((x-({fn_prefix}_cx))**2 + (y-({fn_prefix}_cy))**2)*{fn_prefix}_ln_ba))',")
        lines.append("    '0',")
        lines.append("]")
        lines.append(f"{fn_prefix}_H_expr = [")
        lines.append(f"    '(-{fn_prefix}_prop_sign*(y-({fn_prefix}_cy))/(2*pi*{fn_prefix}_z0*((x-({fn_prefix}_cx))**2 + (y-({fn_prefix}_cy))**2)))',")
        lines.append(f"    '( {fn_prefix}_prop_sign*(x-({fn_prefix}_cx))/(2*pi*{fn_prefix}_z0*((x-({fn_prefix}_cx))**2 + (y-({fn_prefix}_cy))**2)))',")
        lines.append("    '0',")
        lines.append("]")
    elif axis == "x":
        lines.append(f"{fn_prefix}_E_expr = [")
        lines.append("    '0',")
        lines.append(f"    '((y-({fn_prefix}_cy))/(((y-({fn_prefix}_cy))**2 + (z-({fn_prefix}_cz))**2)*{fn_prefix}_ln_ba))',")
        lines.append(f"    '((z-({fn_prefix}_cz))/(((y-({fn_prefix}_cy))**2 + (z-({fn_prefix}_cz))**2)*{fn_prefix}_ln_ba))',")
        lines.append("]")
        lines.append(f"{fn_prefix}_H_expr = [")
        lines.append("    '0',")
        lines.append(f"    '(-{fn_prefix}_prop_sign*(z-({fn_prefix}_cz))/(2*pi*{fn_prefix}_z0*((y-({fn_prefix}_cy))**2 + (z-({fn_prefix}_cz))**2)))',")
        lines.append(f"    '( {fn_prefix}_prop_sign*(y-({fn_prefix}_cy))/(2*pi*{fn_prefix}_z0*((y-({fn_prefix}_cy))**2 + (z-({fn_prefix}_cz))**2)))',")
        lines.append("]")
    else:
        lines.append(f"{fn_prefix}_E_expr = [")
        lines.append(f"    '((x-({fn_prefix}_cx))/(((x-({fn_prefix}_cx))**2 + (z-({fn_prefix}_cz))**2)*{fn_prefix}_ln_ba))',")
        lines.append("    '0',")
        lines.append(f"    '((z-({fn_prefix}_cz))/(((x-({fn_prefix}_cx))**2 + (z-({fn_prefix}_cz))**2)*{fn_prefix}_ln_ba))',")
        lines.append("]")
        lines.append(f"{fn_prefix}_H_expr = [")
        lines.append(f"    '( {fn_prefix}_prop_sign*(z-({fn_prefix}_cz))/(2*pi*{fn_prefix}_z0*((x-({fn_prefix}_cx))**2 + (z-({fn_prefix}_cz))**2)))',")
        lines.append("    '0',")
        lines.append(f"    '(-{fn_prefix}_prop_sign*(x-({fn_prefix}_cx))/(2*pi*{fn_prefix}_z0*((x-({fn_prefix}_cx))**2 + (z-({fn_prefix}_cz))**2)))',")
        lines.append("]")
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
    lines.append(f"    'E_expr': {fn_prefix}_E_expr,")
    lines.append(f"    'H_expr': {fn_prefix}_H_expr,")
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
        if reference_start_stop is not None:
            # openEMS AddWaveGuidePort requires non-zero span along propagation axis.
            start = list(source_start_stop[0])
            stop = list(reference_start_stop[1])
        else:
            start, stop = source_start_stop
        if reverse:
            start, stop = stop, start
        lines.append(
            f"port_{number}_waveguide = _add_waveguide_port(FDTD, {number}, {start}, {stop}, '{direction_axis}', {fn_prefix}_E, {fn_prefix}_H, {fn_prefix}_E_expr, {fn_prefix}_H_expr, 0.0, {excite})"
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
    lines.append("import sys")
    lines.append("from pathlib import Path")
    lines.append("_openems_root = (os.environ.get('OPENEMS_INSTALL_DIR', '') or os.environ.get('OPENEMS_INSTALL_PATH', '')).strip()")
    lines.append("if not _openems_root and os.path.isdir(r'C:\\\\openEMS'):")
    lines.append("    _openems_root = r'C:\\\\openEMS'")
    lines.append("if _openems_root and hasattr(os, 'add_dll_directory'):")
    lines.append("    os.add_dll_directory(_openems_root)")
    lines.append("_openems_py_candidates = []")
    lines.append("if _openems_root:")
    lines.append("    _root = Path(_openems_root)")
    lines.append("    _openems_py_candidates.extend([_root / 'python', _root / 'python' / 'site-packages', _root / 'lib'])")
    lines.append("_extra_py = os.environ.get('OPENEMS_PYTHONPATH', '').strip()")
    lines.append("if _extra_py:")
    lines.append("    _openems_py_candidates.extend(Path(p.strip()) for p in _extra_py.split(os.pathsep) if p.strip())")
    lines.append("for _candidate in _openems_py_candidates:")
    lines.append("    _text = str(_candidate)")
    lines.append("    if _text and os.path.isdir(_text) and _text not in sys.path:")
    lines.append("        sys.path.insert(0, _text)")
    lines.append("import math")
    lines.append("import CSXCAD")
    lines.append("from CSXCAD import CSPrimitives")
    lines.append("import openEMS")
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
    nr_ts, max_time_sec = _derive_run_limits(sim)
    end_criteria = _as_float(sim.get("EndCriteria", 1e-5), 1e-5)
    lines.append(f"FDTD = openEMS.openEMS(NrTS={nr_ts}, EndCriteria={end_criteria})")
    lines.append("FDTD.SetCSX(CSX)")
    lines.append(f"# Run limit contract: NrTS={nr_ts}, MaxTime={max_time_sec} sec")
    lines.append(f"max_time_sec = {max_time_sec}")
    lines.append("if max_time_sec > 0.0:")
    lines.append("    _set_max_time = getattr(FDTD, 'SetMaxTime', None)")
    lines.append("    if callable(_set_max_time):")
    lines.append("        _set_max_time_ok = False")
    lines.append("        _set_max_time_attempts = [")
    lines.append("            lambda: _set_max_time(max_time_sec),")
    lines.append("            lambda: _set_max_time(MaxTime=max_time_sec),")
    lines.append("            lambda: _set_max_time(max_time=max_time_sec),")
    lines.append("        ]")
    lines.append("        for _set_max_time_call in _set_max_time_attempts:")
    lines.append("            try:")
    lines.append("                _set_max_time_call()")
    lines.append("                _set_max_time_ok = True")
    lines.append("                break")
    lines.append("            except TypeError:")
    lines.append("                continue")
    lines.append("        if not _set_max_time_ok:")
    lines.append("            raise RuntimeError('Unable to call SetMaxTime with supported signatures for this openEMS Python build.')")
    _emit_excitation(lines, sim)
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
    geometries_with_primitives = [geo for geo in model.geometries if geo.primitive in {"box", "cylinder", "polyhedron"}]
    has_polyhedron_geometries = any(geo.primitive == "polyhedron" for geo in model.geometries)

    if geometries_with_primitives:
        needs_unassigned = any(
            str(getattr(geo, "assigned_material_name", "") or "").strip() not in material_vars
            for geo in geometries_with_primitives
        )
        if needs_unassigned:
            lines.append("_phase33_unassigned_prop = CSX.AddMaterial('_phase33_unassigned')")
            lines.append("_phase33_unassigned_prop.SetMaterialProperty(epsilon=1.0, mue=1.0, kappa=0.0)")

    if has_polyhedron_geometries:
        lines.append("def _add_polyhedron_reader(prop, stl_path, priority):")
        lines.append("    if not os.path.isfile(stl_path):")
        lines.append("        raise FileNotFoundError(f'STL geometry file not found: {stl_path}')")
        lines.append("    stl_file_type = getattr(CSPrimitives, 'STL_FILE', None)")
        lines.append("    add_reader = getattr(prop, 'AddPolyhedronReader', None)")
        lines.append("    if add_reader is None:")
        lines.append("        raise RuntimeError('CSXCAD property object does not expose AddPolyhedronReader for STL-backed geometry.')")
        lines.append("    attempts = [")
        lines.append("        lambda: add_reader(stl_path, stl_file_type, priority),")
        lines.append("        lambda: add_reader(stl_path, stl_file_type),")
        lines.append("        lambda: add_reader(stl_path),")
        lines.append("        lambda: add_reader(filename=stl_path, file_type=stl_file_type, priority=priority),")
        lines.append("        lambda: add_reader(filename=stl_path, file_type=stl_file_type),")
        lines.append("        lambda: add_reader(filename=stl_path),")
        lines.append("    ]")
        lines.append("    for call in attempts:")
        lines.append("        try:")
        lines.append("            return call()")
        lines.append("        except TypeError:")
        lines.append("            continue")
        lines.append("    reader = add_reader()")
        lines.append("    if reader is None:")
        lines.append("        raise RuntimeError('AddPolyhedronReader returned no reader object for STL-backed geometry.')")
        lines.append("    if hasattr(reader, 'SetFilename'):")
        lines.append("        reader.SetFilename(stl_path)")
        lines.append("    if stl_file_type is not None and hasattr(reader, 'SetFileType'):")
        lines.append("        reader.SetFileType(stl_file_type)")
        lines.append("    if hasattr(reader, 'SetPriority'):")
        lines.append("        reader.SetPriority(priority)")
        lines.append("    read_file = getattr(reader, 'ReadFile', None)")
        lines.append("    if callable(read_file):")
        lines.append("        read_ok = read_file()")
        lines.append("        if read_ok is False:")
        lines.append("            raise RuntimeError(f'Failed to read STL geometry: {stl_path}')")
        lines.append("    return reader")
        lines.append("")

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
            stl_path = _stl_path_for_geometry(geo)
            material_name = str(getattr(geo, "assigned_material_name", "") or "").strip()
            prop_var = material_vars.get(material_name, "_phase33_unassigned_prop")
            priority = _as_int(getattr(geo, "assignment_priority", 0), 0)
            poly_symbol = f"poly_{_safe_symbol(geo.object_name)}"
            lines.append(f"{poly_symbol} = _add_polyhedron_reader({prop_var}, {stl_path!r}, priority={priority})")
            lines.append(
                f"# POLYHEDRON {geo.object_name}: stl={stl_path}"
            )
    lines.append("")

    output_dir = Path(run_output_dir) if run_output_dir else Path("./run")
    lines.append(f"sim_path = Path({str(output_dir)!r})")
    lines.append("sim_path.mkdir(parents=True, exist_ok=True)")
    lines.append("dump_path = sim_path / 'dump'")
    lines.append("dump_path.mkdir(parents=True, exist_ok=True)")
    lines.append("")

    has_waveguide_port = any(str(port.get("PortType", "")).strip() == "Waveguide" for port in model.ports)
    if has_waveguide_port:
        lines.append("# Waveguide port adapter")
        lines.append("def _add_waveguide_port(fdtd, number, start, stop, direction, e_func, h_func, e_expr, h_expr, kc, excite):")
        lines.append("    attempts = [")
        lines.append("        # Canonical signature in current openEMS wheels: AddWaveGuidePort(..., E_func, H_func, kc, excite=0)")
        lines.append("        lambda: fdtd.AddWaveGuidePort(number, start, stop, direction, e_func, h_func, kc, excite),")
        lines.append("        lambda: fdtd.AddWaveGuidePort(number, start, stop, direction, e_func, h_func, kc),")
        lines.append("        lambda: fdtd.AddWaveGuidePort(num=number, start=start, stop=stop, p_dir=direction, E_func=e_func, H_func=h_func, kc=kc, excite=excite),")
        lines.append("        lambda: fdtd.AddWaveGuidePort(num=number, start=start, stop=stop, p_dir=direction, E_func=e_func, H_func=h_func, kc=kc),")
        lines.append("        # Some openEMS builds expect iterable mode expressions rather than Python callables.")
        lines.append("        lambda: fdtd.AddWaveGuidePort(number, start, stop, direction, e_expr, h_expr, kc, excite),")
        lines.append("        lambda: fdtd.AddWaveGuidePort(number, start, stop, direction, e_expr, h_expr, kc),")
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
    lines.append("def _add_e_field_time_dump_plane(csx, dump_directory, start, stop):")
    lines.append("    add_dump = getattr(csx, 'AddDump', None)")
    lines.append("    if not callable(add_dump):")
    lines.append("        raise RuntimeError('CSX object does not expose AddDump required for dump-plane export.')")
    lines.append("    attempts = [")
    lines.append("        lambda: add_dump('Et', dump_directory),")
    lines.append("        lambda: add_dump('Et', subdir=dump_directory),")
    lines.append("        lambda: add_dump('Et', filename=dump_directory),")
    lines.append("        lambda: add_dump('Et'),")
    lines.append("    ]")
    lines.append("    dump_obj = None")
    lines.append("    for call in attempts:")
    lines.append("        try:")
    lines.append("            dump_obj = call()")
    lines.append("            break")
    lines.append("        except TypeError:")
    lines.append("            continue")
    lines.append("    if dump_obj is None:")
    lines.append("        raise RuntimeError('Unable to call AddDump with supported signatures for this openEMS Python build.')")
    lines.append("    add_box = getattr(dump_obj, 'AddBox', None)")
    lines.append("    if not callable(add_box):")
    lines.append("        raise RuntimeError('Dump object does not expose AddBox for plane-region definition.')")
    lines.append("    try:")
    lines.append("        add_box(start, stop)")
    lines.append("    except TypeError:")
    lines.append("        add_box(start=start, stop=stop)")
    lines.append("    return dump_obj")
    bounds = _scaled_simulation_bounds(model.simulation_box or {}, model_scale)
    if bounds is None:
        bounds = _mesh_bounds(x_lines, y_lines, z_lines)
    for dump in model.dumpboxes:
        dump_name = str(dump.get("name", "Dump") or "Dump")
        if not bool(dump.get("Enabled", True)):
            lines.append(f"# DUMP {dump_name}: disabled")
            continue

        dump_type = _normalized_dump_type(str(dump.get("DumpType", "") or ""))
        if dump_type != "EField":
            lines.append(f"# DUMP {dump_name}: skipped (unsupported type '{dump.get('DumpType')}'; MVP supports EField only)")
            continue

        dump_mode = str(dump.get("DumpMode", "") or "TimeDomain").strip()
        if dump_mode != "TimeDomain":
            lines.append(f"# DUMP {dump_name}: skipped (unsupported mode '{dump_mode}'; MVP supports TimeDomain only)")
            continue

        if bounds is None:
            lines.append(f"# DUMP {dump_name}: skipped (simulation bounds unavailable for plane placement)")
            continue

        axis = _normalized_plane_axis(dump.get("PlaneAxis", "Z"))
        start, stop = _plane_start_stop_from_bounds(axis, bounds)
        symbol = f"dump_{_safe_symbol(dump_name)}"
        lines.append(
            f"# DUMP {dump_name}: EField TimeDomain plane axis={axis} start={start} stop={stop}"
        )
        lines.append(
            f"{symbol} = _add_e_field_time_dump_plane(CSX, str(dump_path), {start}, {stop})"
        )
    lines.append("")

    if runnable:
        lines.append("FDTD.Run(str(sim_path), verbose=3)")
        lines.append("print(f'openEMS run completed: {sim_path}')")
    else:
        lines.append("if __name__ == '__main__':")
        lines.append("    print('Dry-run export: model assembled; no FDTD.Run() was executed.')")
        lines.append("    print('Run simulation from FreeCAD with RunSimulation enabled to execute openEMS.')")
        lines.append("# Dry-run export script generated successfully")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
