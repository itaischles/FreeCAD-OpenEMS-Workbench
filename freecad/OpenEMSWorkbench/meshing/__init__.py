from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from typing import Any

try:
	from model import DEFAULTS
	from utils.analysis_context import get_active_analysis, get_proxy_type
except ImportError:
	from OpenEMSWorkbench.model import DEFAULTS
	from OpenEMSWorkbench.utils.analysis_context import get_active_analysis, get_proxy_type


@dataclass(frozen=True)
class MeshLines:
	coordinate_system: str
	x: tuple[float, ...]
	y: tuple[float, ...]
	z: tuple[float, ...]
	radial: tuple[float, ...] = ()
	azimuth: tuple[float, ...] = ()

	@property
	def signature(self) -> str:
		payload = [self.coordinate_system]
		payload.append(",".join(f"{value:.9f}" for value in self.x))
		payload.append(",".join(f"{value:.9f}" for value in self.y))
		payload.append(",".join(f"{value:.9f}" for value in self.z))
		payload.append(",".join(f"{value:.9f}" for value in self.radial))
		payload.append(",".join(f"{value:.9f}" for value in self.azimuth))
		return sha1("|".join(payload).encode("utf-8")).hexdigest()


class MeshResolutionError(ValueError):
	pass


def _to_positive_float(value: Any, fallback: float) -> float:
	try:
		parsed = float(value)
	except Exception:
		return fallback
	return parsed if parsed > 0.0 else fallback


def _to_bool(value: Any, fallback: bool) -> bool:
	if isinstance(value, bool):
		return value
	if value is None:
		return fallback
	return bool(value)


def _graded_axis(half_span: float, base_step: float, max_step: float, grading: float) -> tuple[float, ...]:
	position = 0.0
	step = max(base_step, 1e-9)
	grading = max(grading, 1.0)
	positive: list[float] = []

	while position + step < half_span:
		position += step
		positive.append(position)
		step = min(max_step, step * grading)

	mirrored = [-value for value in reversed(positive)]
	values = mirrored + [0.0] + positive
	return tuple(round(value, 9) for value in values)


def _smooth_axis(values: tuple[float, ...], enabled: bool) -> tuple[float, ...]:
	if not enabled:
		return values
	result: list[float] = []
	for value in values:
		rounded = round(value, 6)
		if result and abs(result[-1] - rounded) < 1e-9:
			continue
		result.append(rounded)
	return tuple(result)


def _extract_grid_parameters(grid_obj: Any) -> tuple[str, float, float, float, bool]:
	defaults = DEFAULTS["grid"]
	coordinate_system = str(
		getattr(grid_obj, "CoordinateSystem", defaults["coordinate_system"])
	)
	base_resolution = _to_positive_float(
		getattr(grid_obj, "BaseResolution", defaults["base_resolution"]),
		defaults["base_resolution"],
	)
	max_resolution = _to_positive_float(
		getattr(grid_obj, "MaxResolution", defaults["max_resolution"]),
		defaults["max_resolution"],
	)
	if max_resolution < base_resolution:
		max_resolution = base_resolution
	grading_factor = _to_positive_float(
		getattr(grid_obj, "GradingFactor", defaults["grading_factor"]),
		defaults["grading_factor"],
	)
	if grading_factor < 1.0:
		grading_factor = 1.0
	auto_smooth = _to_bool(getattr(grid_obj, "AutoSmooth", defaults["auto_smooth"]), True)
	return coordinate_system, base_resolution, max_resolution, grading_factor, auto_smooth


def generate_mesh_from_grid(grid_obj: Any) -> MeshLines:
	if grid_obj is None:
		raise MeshResolutionError("No Grid object provided.")

	coordinate_system, base_res, max_res, grading, auto_smooth = _extract_grid_parameters(grid_obj)
	half_span = max(max_res * 8.0, base_res * 12.0)

	if coordinate_system == "Cylindrical":
		radial: list[float] = [0.0]
		radius = 0.0
		step = base_res
		while radius + step < half_span:
			radius += step
			radial.append(radius)
			step = min(max_res, step * grading)

		radial_axis = tuple(round(value, 9) for value in radial)
		radial_axis = _smooth_axis(radial_axis, auto_smooth)

		z_axis = _smooth_axis(_graded_axis(half_span, base_res, max_res, grading), auto_smooth)

		azimuth_count = 16
		azimuth = tuple(
			round((2.0 * 3.141592653589793 * idx) / azimuth_count, 9)
			for idx in range(azimuth_count)
		)
		return MeshLines(
			coordinate_system="Cylindrical",
			x=(),
			y=(),
			z=z_axis,
			radial=radial_axis,
			azimuth=azimuth,
		)

	x_axis = _smooth_axis(_graded_axis(half_span, base_res, max_res, grading), auto_smooth)
	y_axis = _smooth_axis(_graded_axis(half_span, base_res, max_res, grading), auto_smooth)
	z_axis = _smooth_axis(_graded_axis(half_span, base_res, max_res, grading), auto_smooth)
	return MeshLines(
		coordinate_system="Cartesian",
		x=x_axis,
		y=y_axis,
		z=z_axis,
	)


def resolve_active_analysis_grid(doc: Any) -> tuple[Any, Any]:
	if doc is None:
		raise MeshResolutionError("No active document.")

	analysis = get_active_analysis(doc)
	if analysis is None:
		raise MeshResolutionError("No active analysis found.")

	for member in getattr(analysis, "Group", []):
		if get_proxy_type(member) == "OpenEMS_Grid":
			return analysis, member

	raise MeshResolutionError("Active analysis has no assigned Grid object.")


def build_mesh_for_active_analysis(doc: Any) -> tuple[Any, Any, MeshLines]:
	analysis, grid = resolve_active_analysis_grid(doc)
	mesh = generate_mesh_from_grid(grid)
	return analysis, grid, mesh


__all__ = [
	"MeshLines",
	"MeshResolutionError",
	"generate_mesh_from_grid",
	"resolve_active_analysis_grid",
	"build_mesh_for_active_analysis",
]
