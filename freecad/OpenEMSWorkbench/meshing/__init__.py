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
	preview_line_cap: int = 96

	@property
	def signature(self) -> str:
		payload = [self.coordinate_system]
		payload.append(",".join(f"{value:.9f}" for value in self.x))
		payload.append(",".join(f"{value:.9f}" for value in self.y))
		payload.append(",".join(f"{value:.9f}" for value in self.z))
		payload.append(",".join(f"{value:.9f}" for value in self.radial))
		payload.append(",".join(f"{value:.9f}" for value in self.azimuth))
		payload.append(str(int(self.preview_line_cap)))
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


def _to_float(value: Any, fallback: float = 0.0) -> float:
	if hasattr(value, "Value"):
		try:
			return float(value.Value)
		except Exception:
			return fallback
	try:
		return float(value)
	except Exception:
		return fallback


def _to_positive_int(value: Any, fallback: int) -> int:
	try:
		parsed = int(value)
	except Exception:
		return fallback
	return parsed if parsed > 0 else fallback


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


def _bounded_axis(
	minimum: float,
	maximum: float,
	base_step: float,
	max_step: float,
	grading: float,
) -> tuple[float, ...]:
	if maximum < minimum:
		minimum, maximum = maximum, minimum
	if abs(maximum - minimum) < 1e-12:
		return (round(minimum, 9),)

	position = minimum
	step = max(base_step, 1e-9)
	grading = max(grading, 1.0)
	values = [minimum]

	while position + step < maximum:
		position += step
		values.append(position)
		step = min(max_step, step * grading)

	if values[-1] != maximum:
		values.append(maximum)

	return tuple(round(value, 9) for value in values)


def _vector_component(vector: Any, lower_name: str, upper_name: str) -> float:
	if vector is None:
		return 0.0
	return _to_float(getattr(vector, lower_name, getattr(vector, upper_name, 0.0)), 0.0)


def _simulation_box_extents_from_object(box_obj: Any) -> tuple[float, float, float, float, float, float] | None:
	if box_obj is None:
		return None

	length = _to_float(getattr(box_obj, "Length", 0.0), 0.0)
	width = _to_float(getattr(box_obj, "Width", 0.0), 0.0)
	height = _to_float(getattr(box_obj, "Height", 0.0), 0.0)
	if length <= 0.0 or width <= 0.0 or height <= 0.0:
		return None

	placement = getattr(box_obj, "Placement", None)
	base = getattr(placement, "Base", None)
	start_x = _vector_component(base, "x", "X")
	start_y = _vector_component(base, "y", "Y")
	start_z = _vector_component(base, "z", "Z")

	return (
		start_x,
		start_x + length,
		start_y,
		start_y + width,
		start_z,
		start_z + height,
	)


def _find_simulation_box_object(analysis: Any) -> Any:
	for obj in list(getattr(analysis, "Group", [])):
		if bool(getattr(obj, "OpenEMSSimulationBox", False)):
			return obj
	document = getattr(analysis, "Document", None)
	if document is not None:
		for obj in list(getattr(document, "Objects", [])):
			if bool(getattr(obj, "OpenEMSSimulationBox", False)):
				return obj
	return None


def _parse_simulation_box_dict(box: dict[str, Any]) -> tuple[float, float, float, float, float, float] | None:
	try:
		xmin = _to_float(box.get("XMin"), 0.0)
		xmax = _to_float(box.get("XMax"), 0.0)
		ymin = _to_float(box.get("YMin"), 0.0)
		ymax = _to_float(box.get("YMax"), 0.0)
		zmin = _to_float(box.get("ZMin"), 0.0)
		zmax = _to_float(box.get("ZMax"), 0.0)
	except Exception:
		return None
	if xmax <= xmin or ymax <= ymin or zmax <= zmin:
		return None
	return xmin, xmax, ymin, ymax, zmin, zmax


def _shape_bounds(obj: Any) -> dict[str, float] | None:
	shape = getattr(obj, "Shape", None)
	bb = getattr(shape, "BoundBox", None)
	if bb is None:
		return None
	fields = ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")
	if not all(hasattr(bb, name) for name in fields):
		return None
	return {
		"xmin": _to_float(bb.XMin, 0.0),
		"ymin": _to_float(bb.YMin, 0.0),
		"zmin": _to_float(bb.ZMin, 0.0),
		"xmax": _to_float(bb.XMax, 0.0),
		"ymax": _to_float(bb.YMax, 0.0),
		"zmax": _to_float(bb.ZMax, 0.0),
	}


def _collect_analysis_geometry_bounds(analysis: Any) -> list[dict[str, float]]:
	bounds: list[dict[str, float]] = []
	for obj in list(getattr(analysis, "Group", [])):
		if bool(getattr(obj, "OpenEMSSimulationBox", False)):
			continue
		proxy_type = get_proxy_type(obj)
		if proxy_type.startswith("OpenEMS_"):
			continue
		entry = _shape_bounds(obj)
		if entry is not None:
			bounds.append(entry)
	bounds.sort(key=lambda item: (
		item["xmin"],
		item["ymin"],
		item["zmin"],
		item["xmax"],
		item["ymax"],
		item["zmax"],
	))
	return bounds


def _merge_axis_snaps(
	axis: tuple[float, ...],
	snaps: list[float],
	minimum: float,
	maximum: float,
	merge_tolerance: float = 0.0,
) -> tuple[float, ...]:
	values = [v for v in axis if minimum <= v <= maximum]
	for value in snaps:
		if minimum <= value <= maximum:
			values.append(value)
	merged = sorted({round(v, 9) for v in values})
	if not merged:
		return (round(minimum, 9), round(maximum, 9))

	tolerance = max(_to_float(merge_tolerance, 0.0), 0.0)
	collapsed: list[float] = [merged[0]]
	for value in merged[1:]:
		if tolerance > 0.0 and abs(value - collapsed[-1]) <= tolerance:
			continue
		collapsed.append(value)

	min_r = round(minimum, 9)
	max_r = round(maximum, 9)
	if not collapsed:
		collapsed = [min_r, max_r]
	if abs(collapsed[0] - min_r) <= tolerance:
		collapsed[0] = min_r
	elif collapsed[0] != min_r:
		collapsed.insert(0, min_r)
	if abs(collapsed[-1] - max_r) <= tolerance:
		collapsed[-1] = max_r
	elif collapsed[-1] != max_r:
		collapsed.append(max_r)
	return tuple(collapsed)


def _apply_conservative_snapping(
	mesh: MeshLines,
	simulation_box_extents: tuple[float, float, float, float, float, float],
	geometry_bounds: list[dict[str, float]],
	merge_tolerance: float = 0.0,
) -> MeshLines:
	if not geometry_bounds:
		return mesh

	xmin, xmax, ymin, ymax, zmin, zmax = simulation_box_extents

	if mesh.coordinate_system == "Cartesian":
		x_snaps: list[float] = []
		y_snaps: list[float] = []
		z_snaps: list[float] = []
		for entry in geometry_bounds:
			x_snaps.extend([entry["xmin"], entry["xmax"]])
			y_snaps.extend([entry["ymin"], entry["ymax"]])
			z_snaps.extend([entry["zmin"], entry["zmax"]])
		return MeshLines(
			coordinate_system=mesh.coordinate_system,
			x=_merge_axis_snaps(mesh.x, x_snaps, xmin, xmax, merge_tolerance=merge_tolerance),
			y=_merge_axis_snaps(mesh.y, y_snaps, ymin, ymax, merge_tolerance=merge_tolerance),
			z=_merge_axis_snaps(mesh.z, z_snaps, zmin, zmax, merge_tolerance=merge_tolerance),
			radial=mesh.radial,
			azimuth=mesh.azimuth,
			preview_line_cap=mesh.preview_line_cap,
		)

	if mesh.coordinate_system == "Cylindrical":
		z_snaps: list[float] = []
		radial_snaps: list[float] = []
		if xmin <= 0.0 <= xmax and ymin <= 0.0 <= ymax:
			radial_limit = min(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
		else:
			radial_limit = 0.0
		for entry in geometry_bounds:
			z_snaps.extend([entry["zmin"], entry["zmax"]])
			radial_snaps.extend([
				abs(entry["xmin"]),
				abs(entry["xmax"]),
				abs(entry["ymin"]),
				abs(entry["ymax"]),
			])
		return MeshLines(
			coordinate_system=mesh.coordinate_system,
			x=mesh.x,
			y=mesh.y,
			z=_merge_axis_snaps(mesh.z, z_snaps, zmin, zmax, merge_tolerance=merge_tolerance),
			radial=_merge_axis_snaps(mesh.radial, radial_snaps, 0.0, radial_limit, merge_tolerance=merge_tolerance),
			azimuth=mesh.azimuth,
			preview_line_cap=mesh.preview_line_cap,
		)

	return mesh


def _resolve_simulation_box_extents(analysis: Any) -> tuple[float, float, float, float, float, float]:
	box_obj = _find_simulation_box_object(analysis)
	from_object = _simulation_box_extents_from_object(box_obj)
	if from_object is not None:
		return from_object

	try:
		try:
			from exporter.document_reader import refresh_simulation_box_for_analysis
		except ImportError:
			from OpenEMSWorkbench.exporter.document_reader import refresh_simulation_box_for_analysis
		simulation_box = refresh_simulation_box_for_analysis(analysis)
	except Exception as exc:
		raise MeshResolutionError(
			f"Failed to resolve simulation-box extents for mesh generation: {exc}"
		) from exc

	parsed = _parse_simulation_box_dict(simulation_box or {})
	if parsed is None:
		raise MeshResolutionError(
			"Active analysis has no valid simulation-box extents. Create geometry and refresh the simulation box first."
		)
	return parsed


def _extract_grid_parameters(grid_obj: Any) -> tuple[str, float, float, float, bool, int]:
	defaults = DEFAULTS["grid"]
	coordinate_system = str(
		getattr(grid_obj, "CoordinateSystem", defaults["coordinate_system"])
	)
	base_resolution = _to_positive_float(
		getattr(grid_obj, "MeshBaseStep", defaults["mesh_base_step"]),
		defaults["mesh_base_step"],
	)
	max_resolution = _to_positive_float(
		getattr(grid_obj, "MeshMaxStep", defaults["mesh_max_step"]),
		defaults["mesh_max_step"],
	)
	if max_resolution < base_resolution:
		max_resolution = base_resolution
	grading_factor = _to_positive_float(
		getattr(grid_obj, "MeshGrowthRate", defaults["mesh_growth_rate"]),
		defaults["mesh_growth_rate"],
	)
	if grading_factor < 1.0:
		grading_factor = 1.0
	auto_smooth = _to_bool(getattr(grid_obj, "MeshAutoSmooth", defaults["mesh_auto_smooth"]), True)
	preview_line_cap = _to_positive_int(
		getattr(grid_obj, "MeshPreviewLineCap", defaults["mesh_preview_line_cap"]),
		defaults["mesh_preview_line_cap"],
	)
	return coordinate_system, base_resolution, max_resolution, grading_factor, auto_smooth, preview_line_cap


def generate_mesh_from_grid(
	grid_obj: Any,
	simulation_box_extents: tuple[float, float, float, float, float, float] | None = None,
) -> MeshLines:
	if grid_obj is None:
		raise MeshResolutionError("No Grid object provided.")
	if simulation_box_extents is None:
		raise MeshResolutionError(
			"Simulation-box extents are required for mesh generation. Refresh the simulation box first."
		)

	coordinate_system, base_res, max_res, grading, auto_smooth, preview_line_cap = _extract_grid_parameters(grid_obj)
	xmin, xmax, ymin, ymax, zmin, zmax = simulation_box_extents

	if coordinate_system == "Cylindrical":
		radial: list[float] = [0.0]
		radius = 0.0
		step = base_res
		if xmin <= 0.0 <= xmax and ymin <= 0.0 <= ymax:
			radial_limit = min(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
		else:
			radial_limit = 0.0
		while radius + step < radial_limit:
			radius += step
			radial.append(radius)
			step = min(max_res, step * grading)

		radial_axis = tuple(round(value, 9) for value in radial)
		radial_axis = _smooth_axis(radial_axis, auto_smooth)

		z_axis = _smooth_axis(_bounded_axis(zmin, zmax, base_res, max_res, grading), auto_smooth)

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
			preview_line_cap=preview_line_cap,
		)

	x_axis = _smooth_axis(_bounded_axis(xmin, xmax, base_res, max_res, grading), auto_smooth)
	y_axis = _smooth_axis(_bounded_axis(ymin, ymax, base_res, max_res, grading), auto_smooth)
	z_axis = _smooth_axis(_bounded_axis(zmin, zmax, base_res, max_res, grading), auto_smooth)
	return MeshLines(
		coordinate_system="Cartesian",
		x=x_axis,
		y=y_axis,
		z=z_axis,
		preview_line_cap=preview_line_cap,
	)


def resolve_active_analysis_grid(doc: Any) -> tuple[Any, Any]:
	if doc is None:
		raise MeshResolutionError("No active document.")

	analysis = get_active_analysis(doc)
	return resolve_analysis_grid(analysis)


def resolve_analysis_grid(analysis: Any) -> tuple[Any, Any]:
	if analysis is None:
		raise MeshResolutionError("No active analysis found.")

	for member in getattr(analysis, "Group", []):
		if get_proxy_type(member) == "OpenEMS_Grid":
			return analysis, member

	raise MeshResolutionError("Active analysis has no assigned Grid object.")


def build_mesh_for_analysis(analysis: Any) -> tuple[Any, Any, MeshLines]:
	analysis, grid = resolve_analysis_grid(analysis)
	simulation_box_extents = _resolve_simulation_box_extents(analysis)
	mesh = generate_mesh_from_grid(grid, simulation_box_extents=simulation_box_extents)
	geometry_bounds = _collect_analysis_geometry_bounds(analysis)
	_, base_resolution, _, _, _, _ = _extract_grid_parameters(grid)
	merge_tolerance = max(1e-9, base_resolution * 1e-6)
	mesh = _apply_conservative_snapping(
		mesh,
		simulation_box_extents,
		geometry_bounds,
		merge_tolerance=merge_tolerance,
	)
	return analysis, grid, mesh


def build_mesh_for_active_analysis(doc: Any) -> tuple[Any, Any, MeshLines]:
	analysis, _ = resolve_active_analysis_grid(doc)
	return build_mesh_for_analysis(analysis)


__all__ = [
	"MeshLines",
	"MeshResolutionError",
	"generate_mesh_from_grid",
	"resolve_analysis_grid",
	"resolve_active_analysis_grid",
	"build_mesh_for_analysis",
	"build_mesh_for_active_analysis",
]
