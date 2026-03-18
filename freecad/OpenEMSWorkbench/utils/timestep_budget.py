from __future__ import annotations

import math
from typing import Any


SPEED_OF_LIGHT_M_PER_S = 299_792_458.0
DEFAULT_CFL_FACTOR = 0.99


def _as_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _min_positive_spacing(values: tuple[float, ...]) -> float | None:
    if len(values) < 2:
        return None
    minimum: float | None = None
    for index in range(1, len(values)):
        step = abs(float(values[index]) - float(values[index - 1]))
        if step <= 0.0:
            continue
        if minimum is None or step < minimum:
            minimum = step
    return minimum


def compute_cfl_timestep_seconds(mesh, delta_unit_meters: float, cfl_factor: float = DEFAULT_CFL_FACTOR) -> float:
    delta = _as_float(delta_unit_meters, 0.0)
    if delta <= 0.0:
        raise ValueError("DeltaUnit must be > 0 meters per model unit.")

    factor = _as_float(cfl_factor, DEFAULT_CFL_FACTOR)
    if factor <= 0.0 or factor > 1.0:
        raise ValueError("CFL factor must be in (0, 1].")

    coordinate_system = str(getattr(mesh, "coordinate_system", "Cartesian") or "Cartesian")
    if coordinate_system == "Cartesian":
        dx = _min_positive_spacing(tuple(getattr(mesh, "x", ()) or ()))
        dy = _min_positive_spacing(tuple(getattr(mesh, "y", ()) or ()))
        dz = _min_positive_spacing(tuple(getattr(mesh, "z", ()) or ()))
        if dx is None or dy is None or dz is None:
            raise ValueError("Cartesian mesh must have at least two unique lines per axis.")

        dx_m = dx * delta
        dy_m = dy * delta
        dz_m = dz * delta
        denominator = math.sqrt((1.0 / dx_m) ** 2 + (1.0 / dy_m) ** 2 + (1.0 / dz_m) ** 2)
        dt = factor / (SPEED_OF_LIGHT_M_PER_S * denominator)
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("Computed Cartesian dt is not finite and positive.")
        return dt

    if coordinate_system == "Cylindrical":
        dr = _min_positive_spacing(tuple(getattr(mesh, "radial", ()) or ()))
        dz = _min_positive_spacing(tuple(getattr(mesh, "z", ()) or ()))
        if dr is None or dz is None:
            raise ValueError("Cylindrical mesh must have at least two unique radial and z lines.")

        dr_m = dr * delta
        dz_m = dz * delta
        denominator = math.sqrt((1.0 / dr_m) ** 2 + (1.0 / dz_m) ** 2)
        dt = factor / (SPEED_OF_LIGHT_M_PER_S * denominator)
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("Computed Cylindrical dt is not finite and positive.")
        return dt

    raise ValueError(f"Unsupported mesh coordinate system for dt computation: {coordinate_system}")


def compute_number_of_time_steps(max_time_sec: float, dt_sec: float) -> int:
    t_max = _as_float(max_time_sec, 0.0)
    dt = _as_float(dt_sec, 0.0)
    if t_max <= 0.0:
        raise ValueError("T_max must be > 0 sec.")
    if dt <= 0.0:
        raise ValueError("dt must be > 0 sec.")
    value = int(math.ceil(t_max / dt))
    return max(1, value)


def compute_timestep_budget(mesh, *, delta_unit_meters: float, max_time_sec: float, cfl_factor: float = DEFAULT_CFL_FACTOR) -> tuple[float, int]:
    dt = compute_cfl_timestep_seconds(mesh, delta_unit_meters=delta_unit_meters, cfl_factor=cfl_factor)
    nr_ts = compute_number_of_time_steps(max_time_sec=max_time_sec, dt_sec=dt)
    return dt, nr_ts
