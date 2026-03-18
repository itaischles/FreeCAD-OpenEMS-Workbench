from __future__ import annotations

from typing import Any

try:
    import FreeCAD as App
except ImportError:  # pragma: no cover - FreeCAD runtime only
    App = None

try:
    import Part
except Exception:  # pragma: no cover - FreeCAD runtime only
    Part = None

try:
    from meshing import build_mesh_for_analysis
except ImportError:
    from OpenEMSWorkbench.meshing import build_mesh_for_analysis

try:
    from exporter.port_geometry import detect_waveguide_face_geometry
except ImportError:
    from OpenEMSWorkbench.exporter.port_geometry import detect_waveguide_face_geometry

try:
    from utils.analysis_context import get_proxy_type
except ImportError:
    from OpenEMSWorkbench.utils.analysis_context import get_proxy_type

try:
    from model import DEFAULTS, PORT_TYPES, SIMULATION_BOX_FACE_CHOICES
    from objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )
except ImportError:
    from OpenEMSWorkbench.model import DEFAULTS, PORT_TYPES, SIMULATION_BOX_FACE_CHOICES
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )


_AXIS_FACE_MAP = {
    "XMin": ("x", True),
    "XMax": ("x", False),
    "YMin": ("y", True),
    "YMax": ("y", False),
    "ZMin": ("z", True),
    "ZMax": ("z", False),
}

_SOURCE_OFFSET_MIN = 2
_SOURCE_OFFSET_MAX = 9


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    if hasattr(value, "Value"):
        try:
            return float(value.Value)
        except Exception:
            return fallback
    try:
        return float(value)
    except Exception:
        return fallback


def _normalized_source_plane_offset(value: Any) -> int:
    parsed = _safe_int(value, DEFAULTS["port"]["source_plane_offset_cells"])
    return max(_SOURCE_OFFSET_MIN, min(_SOURCE_OFFSET_MAX, parsed))


def _compute_source_plane_from_mesh(mesh, face_name: str, offset_cells: int) -> dict[str, float | str] | None:
    if getattr(mesh, "coordinate_system", "Cartesian") != "Cartesian":
        return None

    axis_info = _AXIS_FACE_MAP.get(str(face_name))
    if axis_info is None:
        return None

    axis_name, from_min = axis_info
    axis_values = tuple(getattr(mesh, axis_name, ()) or ())
    if len(axis_values) < 2:
        return None

    clamped_offset = _normalized_source_plane_offset(offset_cells)
    if from_min:
        index = min(clamped_offset, len(axis_values) - 1)
    else:
        index = max(0, (len(axis_values) - 1) - clamped_offset)
    axis_value = float(axis_values[index])

    bounds = {
        "xmin": float(mesh.x[0]),
        "xmax": float(mesh.x[-1]),
        "ymin": float(mesh.y[0]),
        "ymax": float(mesh.y[-1]),
        "zmin": float(mesh.z[0]),
        "zmax": float(mesh.z[-1]),
    }

    return {
        "axis": axis_name,
        "coordinate": axis_value,
        **bounds,
    }


def _plane_shape_from_definition(plane_definition: dict[str, float | str]):
    if Part is None:
        return None

    axis = str(plane_definition.get("axis", ""))
    xmin = _safe_float(plane_definition.get("xmin"), 0.0)
    xmax = _safe_float(plane_definition.get("xmax"), 0.0)
    ymin = _safe_float(plane_definition.get("ymin"), 0.0)
    ymax = _safe_float(plane_definition.get("ymax"), 0.0)
    zmin = _safe_float(plane_definition.get("zmin"), 0.0)
    zmax = _safe_float(plane_definition.get("zmax"), 0.0)
    value = _safe_float(plane_definition.get("coordinate"), 0.0)

    if axis == "x":
        points = [
            (value, ymin, zmin),
            (value, ymax, zmin),
            (value, ymax, zmax),
            (value, ymin, zmax),
            (value, ymin, zmin),
        ]
    elif axis == "y":
        points = [
            (xmin, value, zmin),
            (xmax, value, zmin),
            (xmax, value, zmax),
            (xmin, value, zmax),
            (xmin, value, zmin),
        ]
    elif axis == "z":
        points = [
            (xmin, ymin, value),
            (xmax, ymin, value),
            (xmax, ymax, value),
            (xmin, ymax, value),
            (xmin, ymin, value),
        ]
    else:
        return None

    wire = Part.makePolygon([App.Vector(*point) for point in points]) if App is not None else None
    if wire is None:
        return None
    return Part.Face(wire)


def _plane_center_from_definition(plane_definition: dict[str, float | str]) -> tuple[float, float, float]:
    axis_name = str(plane_definition.get("axis", "") or "")
    coordinate = _safe_float(plane_definition.get("coordinate"), 0.0)
    center = [
        0.5 * (_safe_float(plane_definition.get("xmin"), 0.0) + _safe_float(plane_definition.get("xmax"), 0.0)),
        0.5 * (_safe_float(plane_definition.get("ymin"), 0.0) + _safe_float(plane_definition.get("ymax"), 0.0)),
        0.5 * (_safe_float(plane_definition.get("zmin"), 0.0) + _safe_float(plane_definition.get("zmax"), 0.0)),
    ]
    if axis_name == "x":
        center[0] = coordinate
    elif axis_name == "y":
        center[1] = coordinate
    elif axis_name == "z":
        center[2] = coordinate
    return (center[0], center[1], center[2])


def _direction_vector(direction: Any) -> tuple[float, float, float] | None:
    text = str(direction or "").strip().lower()
    mapping = {
        "+x": (1.0, 0.0, 0.0),
        "-x": (-1.0, 0.0, 0.0),
        "+y": (0.0, 1.0, 0.0),
        "-y": (0.0, -1.0, 0.0),
        "+z": (0.0, 0.0, 1.0),
        "-z": (0.0, 0.0, -1.0),
    }
    return mapping.get(text)


def _plane_normal(axis_name: str) -> tuple[float, float, float] | None:
    mapping = {
        "x": (1.0, 0.0, 0.0),
        "y": (0.0, 1.0, 0.0),
        "z": (0.0, 0.0, 1.0),
    }
    return mapping.get(str(axis_name or ""))


def _plane_transverse_span(plane_definition: dict[str, float | str]) -> float:
    axis_name = str(plane_definition.get("axis", "") or "")
    spans = {
        "x": (
            abs(_safe_float(plane_definition.get("ymax"), 0.0) - _safe_float(plane_definition.get("ymin"), 0.0)),
            abs(_safe_float(plane_definition.get("zmax"), 0.0) - _safe_float(plane_definition.get("zmin"), 0.0)),
        ),
        "y": (
            abs(_safe_float(plane_definition.get("xmax"), 0.0) - _safe_float(plane_definition.get("xmin"), 0.0)),
            abs(_safe_float(plane_definition.get("zmax"), 0.0) - _safe_float(plane_definition.get("zmin"), 0.0)),
        ),
        "z": (
            abs(_safe_float(plane_definition.get("xmax"), 0.0) - _safe_float(plane_definition.get("xmin"), 0.0)),
            abs(_safe_float(plane_definition.get("ymax"), 0.0) - _safe_float(plane_definition.get("ymin"), 0.0)),
        ),
    }.get(axis_name, (0.0, 0.0))
    positive = [value for value in spans if value > 0.0]
    return min(positive) if positive else 0.0


def _simulation_box_from_plane_definition(plane_definition: dict[str, float | str]) -> dict[str, float]:
    return {
        "XMin": _safe_float(plane_definition.get("xmin"), 0.0),
        "XMax": _safe_float(plane_definition.get("xmax"), 0.0),
        "YMin": _safe_float(plane_definition.get("ymin"), 0.0),
        "YMax": _safe_float(plane_definition.get("ymax"), 0.0),
        "ZMin": _safe_float(plane_definition.get("zmin"), 0.0),
        "ZMax": _safe_float(plane_definition.get("zmax"), 0.0),
    }


def _coax_circle_center(plane_definition: dict[str, float | str], detection: dict[str, Any] | None) -> tuple[float, float, float] | None:
    if not detection or str(detection.get("status", "")) != "supported":
        return None
    inner = detection.get("inner") or {}
    outer = detection.get("outer") or {}
    inner_center = list(inner.get("center", []) or [])
    outer_center = list(outer.get("center", []) or [])
    if len(inner_center) != 3 and len(outer_center) != 3:
        return None

    if len(inner_center) == 3 and len(outer_center) == 3:
        center = tuple(0.5 * (float(inner_center[idx]) + float(outer_center[idx])) for idx in range(3))
    else:
        source = inner_center if len(inner_center) == 3 else outer_center
        center = (float(source[0]), float(source[1]), float(source[2]))

    axis_name = str(plane_definition.get("axis", "") or "")
    coordinate = _safe_float(plane_definition.get("coordinate"), 0.0)
    if axis_name == "x":
        return (coordinate, center[1], center[2])
    if axis_name == "y":
        return (center[0], coordinate, center[2])
    if axis_name == "z":
        return (center[0], center[1], coordinate)
    return None


def _waveguide_preview_overlay_definition(
    plane_definition: dict[str, float | str],
    propagation_direction: Any,
    detection: dict[str, Any] | None,
) -> dict[str, Any]:
    center = _plane_center_from_definition(plane_definition)
    span = _plane_transverse_span(plane_definition)
    arrow_direction = _direction_vector(propagation_direction)
    arrow_length = span * 0.2 if span > 0.0 else 0.0
    if arrow_length <= 0.0:
        arrow_length = 1.0

    circles = []
    if detection and str(detection.get("status", "")) == "supported":
        circle_center = _coax_circle_center(plane_definition, detection)
        normal = _plane_normal(str(plane_definition.get("axis", "") or ""))
        inner = detection.get("inner") or {}
        outer = detection.get("outer") or {}
        if circle_center is not None and normal is not None:
            inner_radius = _safe_float(inner.get("radius"), 0.0)
            outer_radius = _safe_float(outer.get("radius"), 0.0)
            if inner_radius > 0.0:
                circles.append({"center": circle_center, "radius": inner_radius, "normal": normal})
            if outer_radius > 0.0:
                circles.append({"center": circle_center, "radius": outer_radius, "normal": normal})

    return {
        "center": center,
        "arrow_direction": arrow_direction,
        "arrow_length": arrow_length,
        "circles": circles,
    }


def _waveguide_preview_shape(
    plane_definition: dict[str, float | str],
    propagation_direction: Any,
    detection: dict[str, Any] | None,
):
    face = _plane_shape_from_definition(plane_definition)
    if face is None or Part is None or App is None:
        return face

    overlay = _waveguide_preview_overlay_definition(plane_definition, propagation_direction, detection)
    shapes = [face]

    arrow_direction = overlay.get("arrow_direction")
    arrow_length = _safe_float(overlay.get("arrow_length"), 0.0)
    center = overlay.get("center")
    if arrow_direction is not None and arrow_length > 0.0 and isinstance(center, tuple) and len(center) == 3:
        start = App.Vector(*center)
        direction = App.Vector(*arrow_direction)
        end = App.Vector(
            center[0] + arrow_direction[0] * arrow_length,
            center[1] + arrow_direction[1] * arrow_length,
            center[2] + arrow_direction[2] * arrow_length,
        )
        try:
            shapes.append(Part.makeLine(start, end))
        except Exception:
            pass
        cone_length = max(arrow_length * 0.25, 0.5)
        cone_radius = max(_plane_transverse_span(plane_definition) * 0.025, 0.2)
        cone_base = App.Vector(
            end.x - arrow_direction[0] * cone_length,
            end.y - arrow_direction[1] * cone_length,
            end.z - arrow_direction[2] * cone_length,
        )
        try:
            shapes.append(Part.makeCone(cone_radius, 0.0, cone_length, cone_base, direction))
        except Exception:
            pass

    for circle in list(overlay.get("circles", []) or []):
        try:
            edge = Part.makeCircle(
                float(circle.get("radius", 0.0)),
                App.Vector(*circle.get("center", (0.0, 0.0, 0.0))),
                App.Vector(*circle.get("normal", (0.0, 0.0, 1.0))),
            )
            shapes.append(edge)
        except Exception:
            continue

    if len(shapes) == 1:
        return face
    try:
        return Part.makeCompound(shapes)
    except Exception:
        return face


class OpenEMSPortProxy(FeatureProxyBase):
    TYPE = "OpenEMS_Port"

    def _log_preview_status(self, message: str) -> None:
        text = str(message or "")
        if App is not None and hasattr(App, "Console"):
            try:
                App.Console.PrintMessage(f"OpenEMS: {text}\n")
            except Exception:
                pass

    def _preview_result(self, shown: bool, message: str) -> tuple[bool, str]:
        self._log_preview_status(message)
        return shown, message

    def _normalize_offset_property(self, obj) -> None:
        if bool(getattr(self, "_is_normalizing_offset", False)):
            return

        current = getattr(obj, "SourcePlaneOffsetCells", DEFAULTS["port"]["source_plane_offset_cells"])
        normalized = _normalized_source_plane_offset(current)
        if _safe_int(current, normalized) == normalized:
            return

        try:
            self._is_normalizing_offset = True
            obj.SourcePlaneOffsetCells = normalized
        except Exception:
            pass
        finally:
            self._is_normalizing_offset = False

    def _find_owner_analysis(self, obj):
        document = getattr(obj, "Document", None)
        if document is None:
            return None

        for candidate in list(getattr(document, "Objects", [])):
            if get_proxy_type(candidate) != "OpenEMS_Analysis":
                continue
            if obj in list(getattr(candidate, "Group", [])):
                return candidate
        return None

    def _collect_geometry_objects(self, analysis) -> list[Any]:
        geometry = []
        for candidate in list(getattr(analysis, "Group", [])):
            if bool(getattr(candidate, "OpenEMSSimulationBox", False)):
                continue
            proxy_type = get_proxy_type(candidate)
            if proxy_type.startswith("OpenEMS_"):
                continue
            if hasattr(candidate, "Shape"):
                geometry.append(candidate)
        geometry.sort(key=lambda item: str(getattr(item, "Name", "")))
        return geometry

    def _find_preview_object(self, obj):
        document = getattr(obj, "Document", None)
        if document is None:
            return None
        port_name = str(getattr(obj, "Name", "") or "")
        for candidate in list(getattr(document, "Objects", [])):
            if not bool(getattr(candidate, "OpenEMSWaveguidePortPlane", False)):
                continue
            if str(getattr(candidate, "OpenEMSWaveguidePortName", "") or "") == port_name:
                return candidate

        return None

    def _create_preview_object(self, obj):
        document = getattr(obj, "Document", None)
        if document is None or not hasattr(document, "addObject"):
            return None

        port_name = str(getattr(obj, "Name", "") or "")

        try:
            preview = document.addObject("Part::Feature", "OpenEMSWaveguidePortPlane")
        except Exception:
            return None

        if hasattr(preview, "addProperty") and not hasattr(preview, "OpenEMSWaveguidePortPlane"):
            try:
                preview.addProperty(
                    "App::PropertyBool",
                    "OpenEMSWaveguidePortPlane",
                    "OpenEMS",
                    "Marks helper object used to visualize waveguide source-plane location.",
                )
            except Exception:
                pass
        try:
            preview.OpenEMSWaveguidePortPlane = True
        except Exception:
            pass

        if hasattr(preview, "addProperty") and not hasattr(preview, "OpenEMSWaveguidePortName"):
            try:
                preview.addProperty(
                    "App::PropertyString",
                    "OpenEMSWaveguidePortName",
                    "OpenEMS",
                    "Owning OpenEMS port object name.",
                )
            except Exception:
                pass
        try:
            preview.OpenEMSWaveguidePortName = port_name
        except Exception:
            pass

        return preview

    def _hide_preview(self, obj) -> None:
        preview = self._find_preview_object(obj)
        if preview is None:
            return
        view_obj = getattr(preview, "ViewObject", None)
        if view_obj is not None:
            try:
                view_obj.Visibility = False
            except Exception:
                pass

    def _refresh_waveguide_preview(self, obj) -> tuple[bool, str]:
        if str(getattr(obj, "PortType", "") or "") != "Waveguide":
            self._hide_preview(obj)
            return self._preview_result(False, "Waveguide preview hidden: port type is not Waveguide.")

        analysis = self._find_owner_analysis(obj)
        if analysis is None:
            self._hide_preview(obj)
            return self._preview_result(False, "Waveguide preview hidden: could not find owning analysis.")

        try:
            _, _, mesh = build_mesh_for_analysis(analysis)
        except Exception as exc:
            self._hide_preview(obj)
            return self._preview_result(
                False,
                f"Waveguide preview hidden: mesh is unavailable ({exc}).",
            )

        plane_definition = _compute_source_plane_from_mesh(
            mesh,
            face_name=str(getattr(obj, "SimulationBoxFace", DEFAULTS["port"]["simulation_box_face"]) or ""),
            offset_cells=_normalized_source_plane_offset(
                getattr(obj, "SourcePlaneOffsetCells", DEFAULTS["port"]["source_plane_offset_cells"]),
            ),
        )
        if plane_definition is None:
            self._hide_preview(obj)
            return self._preview_result(
                False,
                "Waveguide preview hidden: could not compute source-plane from current mesh/face.",
            )

        detection = detect_waveguide_face_geometry(
            geometry_objects=self._collect_geometry_objects(analysis),
            simulation_box=_simulation_box_from_plane_definition(plane_definition),
            selected_face=str(getattr(obj, "SimulationBoxFace", DEFAULTS["port"]["simulation_box_face"]) or ""),
        )

        shape = _waveguide_preview_shape(
            plane_definition,
            propagation_direction=getattr(obj, "PropagationDirection", DEFAULTS["port"]["propagation_direction"]),
            detection=detection,
        )
        if shape is None:
            self._hide_preview(obj)
            return self._preview_result(False, "Waveguide preview hidden: failed to build preview face geometry.")

        preview = self._find_preview_object(obj)
        if preview is None:
            preview = self._create_preview_object(obj)
        if preview is None:
            return self._preview_result(False, "Waveguide preview hidden: failed to create preview object.")

        try:
            preview.Shape = shape
            preview.Label = f"Waveguide Plane ({getattr(obj, 'Label', getattr(obj, 'Name', 'Port'))})"
        except Exception:
            return self._preview_result(False, "Waveguide preview hidden: failed to assign preview shape.")

        view_obj = getattr(preview, "ViewObject", None)
        if view_obj is not None:
            try:
                view_obj.Visibility = True
            except Exception:
                pass
            try:
                view_obj.Transparency = 45
            except Exception:
                pass
            try:
                view_obj.ShapeColor = (0.95, 0.5, 0.1)
            except Exception:
                pass
            try:
                view_obj.LineColor = (0.95, 0.35, 0.05)
            except Exception:
                pass
            try:
                view_obj.PointColor = (0.95, 0.35, 0.05)
            except Exception:
                pass
            try:
                view_obj.DisplayMode = "Flat Lines"
            except Exception:
                pass
        document = getattr(obj, "Document", None)
        if document is not None:
            try:
                document.recompute()
            except Exception:
                pass
        return self._preview_result(True, "Waveguide preview shown.")

    def ensure_properties(self, obj):
        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "PortType",
            "Port",
            "Port type definition.",
            DEFAULTS["port"]["port_type"],
        )
        set_enum_choices(
            obj,
            "PortType",
            PORT_TYPES,
            DEFAULTS["port"]["port_type"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyInteger",
            "PortNumber",
            "Port",
            "Port index in simulation.",
            DEFAULTS["port"]["port_number"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "Resistance",
            "Port",
            "Reference resistance in Ohms.",
            DEFAULTS["port"]["resistance"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "Excite",
            "Port",
            "Enable excitation on this port.",
            DEFAULTS["port"]["excite"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "SimulationBoxFace",
            "Waveguide",
            "Simulation-box face that this waveguide port attaches to.",
            DEFAULTS["port"]["simulation_box_face"],
        )
        set_enum_choices(
            obj,
            "SimulationBoxFace",
            SIMULATION_BOX_FACE_CHOICES,
            DEFAULTS["port"]["simulation_box_face"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyInteger",
            "SourcePlaneOffsetCells",
            "Waveguide",
            "Number of mesh cells that place the source plane inside the selected simulation-box face.",
            DEFAULTS["port"]["source_plane_offset_cells"],
        )
        self._normalize_offset_property(obj)
        add_property_if_missing(
            obj,
            "App::PropertyString",
            "PropagationDirection",
            "Port",
            "Primary propagation direction (+x, -x, +y, -y, +z, -z).",
            DEFAULTS["port"]["propagation_direction"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStartX",
            "Port",
            "Port region start X coordinate.",
            DEFAULTS["port"]["start_x"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStartY",
            "Port",
            "Port region start Y coordinate.",
            DEFAULTS["port"]["start_y"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStartZ",
            "Port",
            "Port region start Z coordinate.",
            DEFAULTS["port"]["start_z"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStopX",
            "Port",
            "Port region stop X coordinate.",
            DEFAULTS["port"]["stop_x"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStopY",
            "Port",
            "Port region stop Y coordinate.",
            DEFAULTS["port"]["stop_y"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStopZ",
            "Port",
            "Port region stop Z coordinate.",
            DEFAULTS["port"]["stop_z"],
        )

    def execute(self, obj) -> None:
        _ = obj

    def onChanged(self, obj, prop: str) -> None:  # noqa: N802 - FreeCAD API
        if bool(getattr(self, "_is_restoring", False)):
            return
        if prop == "SourcePlaneOffsetCells":
            self._normalize_offset_property(obj)


class OpenEMSPortViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_PortView"
