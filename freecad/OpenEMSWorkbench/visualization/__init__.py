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


def _build_cartesian_segments(mesh: MeshLines) -> list[list[tuple[float, float, float]]]:
	if not mesh.x or not mesh.y:
		return []
	x_min, x_max = mesh.x[0], mesh.x[-1]
	y_min, y_max = mesh.y[0], mesh.y[-1]

	segments: list[list[tuple[float, float, float]]] = []
	for y_value in mesh.y:
		segments.append([(x_min, y_value, 0.0), (x_max, y_value, 0.0)])
	for x_value in mesh.x:
		segments.append([(x_value, y_min, 0.0), (x_value, y_max, 0.0)])
	if mesh.z:
		z_min, z_max = mesh.z[0], mesh.z[-1]
		for x_value in mesh.x[:: max(1, len(mesh.x) // 8)]:
			segments.append([(x_value, 0.0, z_min), (x_value, 0.0, z_max)])
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
