from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin

try:
	import FreeCADGui as Gui
except ImportError:  # pragma: no cover - FreeCAD runtime only
	Gui = None

try:
	from pivy import coin
except Exception:  # pragma: no cover - available only in FreeCAD runtime
	coin = None

try:
	from meshing import MeshLines
except ImportError:
	from OpenEMSWorkbench.meshing import MeshLines


@dataclass
class _OverlayState:
	separator: object
	signature: str


_ACTIVE_OVERLAY: _OverlayState | None = None


def _runtime_ready() -> bool:
	return Gui is not None and coin is not None and Gui.ActiveDocument is not None


def _active_scene_graph():
	if not _runtime_ready():
		return None
	active_view = getattr(Gui.ActiveDocument, "ActiveView", None)
	if active_view is None:
		return None
	return active_view.getSceneGraph()


def _sample_axis(values: tuple[float, ...], max_count: int) -> tuple[float, ...]:
	if max_count <= 0:
		return tuple()
	if len(values) <= max_count:
		return tuple(values)

	last_index = len(values) - 1
	if max_count == 1:
		return (values[0],)

	indices: list[int] = []
	for idx in range(max_count):
		position = round((idx * last_index) / (max_count - 1))
		indices.append(int(position))

	unique_indices = sorted(set(indices))
	if unique_indices[0] != 0:
		unique_indices.insert(0, 0)
	if unique_indices[-1] != last_index:
		unique_indices.append(last_index)

	return tuple(values[index] for index in unique_indices)


def _build_cartesian_segments(mesh: MeshLines) -> list[list[tuple[float, float, float]]]:
	if not mesh.x or not mesh.y or not mesh.z:
		return []
	x_min, x_max = mesh.x[0], mesh.x[-1]
	y_min, y_max = mesh.y[0], mesh.y[-1]
	z_min, z_max = mesh.z[0], mesh.z[-1]
	x_mid = 0.5 * (x_min + x_max)
	y_mid = 0.5 * (y_min + y_max)
	z_mid = 0.5 * (z_min + z_max)

	# Dense meshes are decimated deterministically for readability, but keep
	# enough lines so resolution changes remain clearly visible to users.
	preview_cap = max(4, int(getattr(mesh, "preview_line_cap", 96)))
	x_lines = _sample_axis(mesh.x, preview_cap)
	y_lines = _sample_axis(mesh.y, preview_cap)
	z_lines = _sample_axis(mesh.z, preview_cap)

	segments: list[list[tuple[float, float, float]]] = []

	# XY plane at simulation mid-height.
	for y_value in y_lines:
		segments.append([(x_min, y_value, z_mid), (x_max, y_value, z_mid)])
	for x_value in x_lines:
		segments.append([(x_value, y_min, z_mid), (x_value, y_max, z_mid)])

	# XZ plane at simulation mid-depth.
	for z_value in z_lines:
		segments.append([(x_min, y_mid, z_value), (x_max, y_mid, z_value)])
	for x_value in x_lines:
		segments.append([(x_value, y_mid, z_min), (x_value, y_mid, z_max)])

	# YZ plane at simulation mid-width.
	for z_value in z_lines:
		segments.append([(x_mid, y_min, z_value), (x_mid, y_max, z_value)])
	for y_value in y_lines:
		segments.append([(x_mid, y_value, z_min), (x_mid, y_value, z_max)])

	# Add box edges for 3D context.
	segments.extend(
		[
			[(x_min, y_min, z_min), (x_max, y_min, z_min)],
			[(x_min, y_max, z_min), (x_max, y_max, z_min)],
			[(x_min, y_min, z_max), (x_max, y_min, z_max)],
			[(x_min, y_max, z_max), (x_max, y_max, z_max)],
			[(x_min, y_min, z_min), (x_min, y_max, z_min)],
			[(x_max, y_min, z_min), (x_max, y_max, z_min)],
			[(x_min, y_min, z_max), (x_min, y_max, z_max)],
			[(x_max, y_min, z_max), (x_max, y_max, z_max)],
			[(x_min, y_min, z_min), (x_min, y_min, z_max)],
			[(x_max, y_min, z_min), (x_max, y_min, z_max)],
			[(x_min, y_max, z_min), (x_min, y_max, z_max)],
			[(x_max, y_max, z_min), (x_max, y_max, z_max)],
		]
	)
	return segments


def _build_cylindrical_segments(mesh: MeshLines) -> list[list[tuple[float, float, float]]]:
	if not mesh.radial:
		return []
	angles = mesh.azimuth or tuple(
		(2.0 * 3.141592653589793 * idx) / 24 for idx in range(24)
	)

	segments: list[list[tuple[float, float, float]]] = []

	for radius in mesh.radial:
		if radius <= 0.0:
			continue
		circle = [(radius * cos(angle), radius * sin(angle), 0.0) for angle in angles]
		circle.append(circle[0])
		segments.append(circle)

	max_radius = mesh.radial[-1]
	for angle in angles:
		segments.append([(0.0, 0.0, 0.0), (max_radius * cos(angle), max_radius * sin(angle), 0.0)])

	if mesh.z:
		z_min, z_max = mesh.z[0], mesh.z[-1]
		segments.append([(0.0, 0.0, z_min), (0.0, 0.0, z_max)])

	return segments


def _build_segments(mesh: MeshLines) -> list[list[tuple[float, float, float]]]:
	if mesh.coordinate_system == "Cylindrical":
		return _build_cylindrical_segments(mesh)
	return _build_cartesian_segments(mesh)


def _preview_diagnostics(mesh: MeshLines) -> str:
	if mesh.coordinate_system == "Cartesian":
		preview_cap = max(4, int(getattr(mesh, "preview_line_cap", 96)))
		sampled_x = len(_sample_axis(mesh.x, preview_cap))
		sampled_y = len(_sample_axis(mesh.y, preview_cap))
		sampled_z = len(_sample_axis(mesh.z, preview_cap))
		return (
			f"cap={preview_cap}, raw(x/y/z)={len(mesh.x)}/{len(mesh.y)}/{len(mesh.z)}, "
			f"shown(x/y/z)={sampled_x}/{sampled_y}/{sampled_z}"
		)

	if mesh.coordinate_system == "Cylindrical":
		preview_cap = max(4, int(getattr(mesh, "preview_line_cap", 96)))
		sampled_radial = len(_sample_axis(mesh.radial, preview_cap))
		sampled_z = len(_sample_axis(mesh.z, preview_cap))
		return (
			f"cap={preview_cap}, raw(radial/z)={len(mesh.radial)}/{len(mesh.z)}, "
			f"shown(radial/z)={sampled_radial}/{sampled_z}"
		)

	return ""


def _build_overlay_separator(mesh: MeshLines):
	segments = _build_segments(mesh)

	separator = coin.SoSeparator()

	draw_style = coin.SoDrawStyle()
	draw_style.lineWidth = 1.0

	material = coin.SoMaterial()
	material.diffuseColor = coin.SbColor(0.15, 0.6, 0.85)

	coords = coin.SoCoordinate3()
	line_set = coin.SoLineSet()

	points: list[tuple[float, float, float]] = []
	num_vertices: list[int] = []
	for segment in segments:
		if len(segment) < 2:
			continue
		points.extend(segment)
		num_vertices.append(len(segment))

	if points:
		coords.point.setValues(0, len(points), points)
		line_set.numVertices.setValues(0, len(num_vertices), num_vertices)

	separator.addChild(draw_style)
	separator.addChild(material)
	separator.addChild(coords)
	separator.addChild(line_set)
	return separator


def show_overlay(mesh: MeshLines) -> tuple[bool, str]:
	global _ACTIVE_OVERLAY
	scene_graph = _active_scene_graph()
	if scene_graph is None:
		return False, "OpenEMS: Mesh overlay unavailable (no active 3D view)."

	if _ACTIVE_OVERLAY is not None:
		try:
			scene_graph.removeChild(_ACTIVE_OVERLAY.separator)
		except Exception:
			pass
		_ACTIVE_OVERLAY = None

	separator = _build_overlay_separator(mesh)
	scene_graph.addChild(separator)
	_ACTIVE_OVERLAY = _OverlayState(separator=separator, signature=mesh.signature)
	details = _preview_diagnostics(mesh)
	if details:
		return True, f"OpenEMS: Mesh overlay shown ({details})."
	return True, "OpenEMS: Mesh overlay shown."


def hide_overlay() -> tuple[bool, str]:
	global _ACTIVE_OVERLAY
	scene_graph = _active_scene_graph()
	if _ACTIVE_OVERLAY is None:
		return False, "OpenEMS: Mesh overlay already hidden."

	if scene_graph is not None:
		try:
			scene_graph.removeChild(_ACTIVE_OVERLAY.separator)
		except Exception:
			pass
	_ACTIVE_OVERLAY = None
	return True, "OpenEMS: Mesh overlay hidden."


def refresh_overlay(mesh: MeshLines) -> tuple[bool, str]:
	if _ACTIVE_OVERLAY is not None and _ACTIVE_OVERLAY.signature == mesh.signature:
		return False, "OpenEMS: Mesh unchanged, overlay refresh skipped."
	return show_overlay(mesh)


def is_overlay_visible() -> bool:
	return _ACTIVE_OVERLAY is not None


def clear_overlay() -> None:
	hide_overlay()


__all__ = [
	"show_overlay",
	"hide_overlay",
	"refresh_overlay",
	"is_overlay_visible",
	"clear_overlay",
]
