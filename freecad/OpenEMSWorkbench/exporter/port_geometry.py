from __future__ import annotations

from collections import defaultdict

try:
    from exporter.geometry_classifier import classify_geometry_object
except ImportError:
    from OpenEMSWorkbench.exporter.geometry_classifier import classify_geometry_object


_FACE_AXIS = {
    "XMin": ("x", True),
    "XMax": ("x", False),
    "YMin": ("y", True),
    "YMax": ("y", False),
    "ZMin": ("z", True),
    "ZMax": ("z", False),
}


def _transverse_center(center: list[float] | tuple[float, float, float], axis_name: str) -> tuple[float, float]:
    cx, cy, cz = center
    if axis_name == "x":
        return (float(cy), float(cz))
    if axis_name == "y":
        return (float(cx), float(cz))
    return (float(cx), float(cy))


def _as_float(value, default: float = 0.0) -> float:
    if hasattr(value, "Value"):
        try:
            return float(value.Value)
        except Exception:
            return default
    try:
        return float(value)
    except Exception:
        return default


def _shape_bounds(obj) -> dict[str, float] | None:
    shape = getattr(obj, "Shape", None)
    bb = getattr(shape, "BoundBox", None)
    if bb is None:
        return None
    fields = ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")
    if not all(hasattr(bb, key) for key in fields):
        return None
    return {
        "xmin": _as_float(bb.XMin),
        "xmax": _as_float(bb.XMax),
        "ymin": _as_float(bb.YMin),
        "ymax": _as_float(bb.YMax),
        "zmin": _as_float(bb.ZMin),
        "zmax": _as_float(bb.ZMax),
    }


def _placement_offset(obj) -> tuple[float, float, float]:
    placement = getattr(obj, "Placement", None)
    base = getattr(placement, "Base", None)
    if base is None:
        return (0.0, 0.0, 0.0)
    return (
        _as_float(getattr(base, "x", getattr(base, "X", 0.0)), 0.0),
        _as_float(getattr(base, "y", getattr(base, "Y", 0.0)), 0.0),
        _as_float(getattr(base, "z", getattr(base, "Z", 0.0)), 0.0),
    )


def _offset_bounds(bounds: dict[str, float], offset: tuple[float, float, float]) -> dict[str, float]:
    dx, dy, dz = offset
    return {
        "xmin": bounds["xmin"] + dx,
        "xmax": bounds["xmax"] + dx,
        "ymin": bounds["ymin"] + dy,
        "ymax": bounds["ymax"] + dy,
        "zmin": bounds["zmin"] + dz,
        "zmax": bounds["zmax"] + dz,
    }


def _candidate_bounds(obj, inherited_offset: tuple[float, float, float]) -> list[dict[str, float]]:
    bounds = _shape_bounds(obj)
    if bounds is None:
        return []

    candidates = [bounds]
    total_offset = tuple(sum(values) for values in zip(inherited_offset, _placement_offset(obj)))
    if any(abs(value) > 1e-12 for value in total_offset):
        shifted = _offset_bounds(bounds, total_offset)
        if shifted != bounds:
            candidates.append(shifted)
    return candidates


def _child_geometry_objects(obj) -> list:
    children = []
    for attr in ("Group", "OutList"):
        value = getattr(obj, attr, None)
        if not isinstance(value, (list, tuple)):
            continue
        for child in value:
            if child is None or child is obj:
                continue
            children.append(child)

    linked = getattr(obj, "LinkedObject", None)
    if linked is not None and linked is not obj:
        children.append(linked)

    unique = []
    seen = set()
    for child in children:
        marker = id(child)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(child)
    unique.sort(key=lambda item: str(getattr(item, "Name", "")))
    return unique


def _iter_leaf_geometry_objects(geometry_objects: list) -> list:
    leaf_objects = []
    seen = set()
    stack = [
        (item, (0.0, 0.0, 0.0))
        for item in sorted(geometry_objects or [], key=lambda item: str(getattr(item, "Name", "")), reverse=True)
    ]

    while stack:
        obj, inherited_offset = stack.pop()
        marker = id(obj)
        if marker in seen:
            continue
        seen.add(marker)

        children = [child for child in _child_geometry_objects(obj) if _shape_bounds(child) is not None]
        if children:
            next_offset = tuple(sum(values) for values in zip(inherited_offset, _placement_offset(obj)))
            stack.extend((child, next_offset) for child in reversed(children))
            continue

        bounds_candidates = _candidate_bounds(obj, inherited_offset)
        if bounds_candidates:
            leaf_objects.append((obj, bounds_candidates))

    return leaf_objects


def _face_coordinate(simulation_box: dict, face_name: str) -> float | None:
    key = {
        "XMin": "XMin",
        "XMax": "XMax",
        "YMin": "YMin",
        "YMax": "YMax",
        "ZMin": "ZMin",
        "ZMax": "ZMax",
    }.get(face_name)
    if key is None:
        return None
    return _as_float(simulation_box.get(key), None)


def _touches_selected_face(
    bounds: dict[str, float],
    axis_name: str,
    face_value: float,
    from_min: bool,
    tolerance: float,
) -> bool:
    axis_min = bounds[f"{axis_name}min"]
    axis_max = bounds[f"{axis_name}max"]

    if from_min:
        return abs(axis_min - face_value) <= tolerance and axis_max > face_value + tolerance
    return abs(axis_max - face_value) <= tolerance and axis_min < face_value - tolerance


def _estimate_axis_aligned_cylinder_from_bounds(
    bounds: dict[str, float],
    tolerance: float,
) -> dict[str, object] | None:
    dx = bounds["xmax"] - bounds["xmin"]
    dy = bounds["ymax"] - bounds["ymin"]
    dz = bounds["zmax"] - bounds["zmin"]
    if min(dx, dy, dz) <= tolerance:
        return None

    profile_tol = max(tolerance, max(dx, dy, dz) * 1e-3)

    xy_equal = abs(dx - dy) <= profile_tol
    xz_equal = abs(dx - dz) <= profile_tol
    yz_equal = abs(dy - dz) <= profile_tol

    # Ambiguous (close to sphere/cube) or no circular profile.
    if (xy_equal and xz_equal and yz_equal) or (not xy_equal and not xz_equal and not yz_equal):
        return None

    if yz_equal and not xy_equal and not xz_equal:
        axis = "x"
        radius = 0.5 * dy
        center = (
            0.5 * (bounds["xmin"] + bounds["xmax"]),
            0.5 * (bounds["ymin"] + bounds["ymax"]),
            0.5 * (bounds["zmin"] + bounds["zmax"]),
        )
    elif xz_equal and not xy_equal and not yz_equal:
        axis = "y"
        radius = 0.5 * dx
        center = (
            0.5 * (bounds["xmin"] + bounds["xmax"]),
            0.5 * (bounds["ymin"] + bounds["ymax"]),
            0.5 * (bounds["zmin"] + bounds["zmax"]),
        )
    elif xy_equal and not xz_equal and not yz_equal:
        axis = "z"
        radius = 0.5 * dx
        center = (
            0.5 * (bounds["xmin"] + bounds["xmax"]),
            0.5 * (bounds["ymin"] + bounds["ymax"]),
            0.5 * (bounds["zmin"] + bounds["zmax"]),
        )
    else:
        return None

    return {
        "axis": axis,
        "radius": radius,
        "center": center,
    }


def _tube_like_radius_info(obj) -> dict[str, float] | None:
    has_outer = hasattr(obj, "OuterRadius")
    has_inner = hasattr(obj, "InnerRadius")
    if not has_outer and not has_inner:
        return None

    outer_radius = _as_float(getattr(obj, "OuterRadius", 0.0), 0.0)
    inner_radius = _as_float(getattr(obj, "InnerRadius", 0.0), 0.0)
    if outer_radius <= 0.0:
        return None
    return {
        "radius": outer_radius,
        "inner_radius": inner_radius if inner_radius > 0.0 else 0.0,
    }


def _cylinder_like_radius_info(obj) -> dict[str, float] | None:
    if not hasattr(obj, "Radius"):
        return None
    radius = _as_float(getattr(obj, "Radius", 0.0), 0.0)
    if radius <= 0.0:
        return None
    return {"radius": radius, "inner_radius": 0.0}


def _radius_info_from_object(obj, bounds_inferred: dict[str, object] | None) -> dict[str, float | str] | None:
    if bounds_inferred is None:
        return None

    tube_info = _tube_like_radius_info(obj)
    if tube_info is not None:
        return {
            "radius": float(tube_info["radius"]),
            "inner_radius": float(tube_info.get("inner_radius", 0.0)),
            "source": "tube_properties",
        }

    cylinder_info = _cylinder_like_radius_info(obj)
    if cylinder_info is not None:
        return {
            "radius": float(cylinder_info["radius"]),
            "inner_radius": float(cylinder_info.get("inner_radius", 0.0)),
            "source": "cylinder_properties",
        }

    return {
        "radius": float(bounds_inferred["radius"]),
        "inner_radius": 0.0,
        "source": "bounds",
    }


def _axis_name_from_vector(vector) -> str | None:
    if vector is None:
        return None
    x = abs(_as_float(getattr(vector, "x", getattr(vector, "X", 0.0)), 0.0))
    y = abs(_as_float(getattr(vector, "y", getattr(vector, "Y", 0.0)), 0.0))
    z = abs(_as_float(getattr(vector, "z", getattr(vector, "Z", 0.0)), 0.0))
    dominant = max((x, "x"), (y, "y"), (z, "z"), key=lambda item: item[0])
    return dominant[1] if dominant[0] > 0.0 else None


def _center_from_bounds(bounds: dict[str, float]) -> tuple[float, float, float]:
    return (
        0.5 * (bounds["xmin"] + bounds["xmax"]),
        0.5 * (bounds["ymin"] + bounds["ymax"]),
        0.5 * (bounds["zmin"] + bounds["zmax"]),
    )


def _axis_hint_from_object(obj) -> str | None:
    for attr in ("Axis", "Direction", "Dir"):
        axis_name = _axis_name_from_vector(getattr(obj, attr, None))
        if axis_name is not None:
            return axis_name

    if _tube_like_radius_info(obj) is not None or _cylinder_like_radius_info(obj) is not None:
        if hasattr(obj, "Height"):
            return "z"
    return None


def _inferred_axis_aligned_cylinder(obj, bounds: dict[str, float], tolerance: float) -> dict[str, object] | None:
    inferred = _estimate_axis_aligned_cylinder_from_bounds(bounds, tolerance)
    axis_hint = _axis_hint_from_object(obj)

    if inferred is not None:
        if axis_hint is not None and str(inferred.get("axis", "")) != axis_hint:
            inferred = dict(inferred)
            inferred["axis"] = axis_hint
        return inferred

    if axis_hint is None:
        return None

    return {
        "axis": axis_hint,
        "radius": 0.0,
        "center": _center_from_bounds(bounds),
    }


def _has_cylindrical_surface_along_axis(obj, axis_name: str) -> bool:
    shape = getattr(obj, "Shape", None)
    faces = getattr(shape, "Faces", None)
    if not faces:
        return False

    for face in faces:
        surface = getattr(face, "Surface", None)
        if surface is None:
            continue
        surface_type = type(surface).__name__
        if "Cylinder" not in surface_type:
            continue
        surface_axis = _axis_name_from_vector(getattr(surface, "Axis", None))
        if surface_axis is None or surface_axis == axis_name:
            return True
    return False


def _support_reason_for_cylinder_like_object(obj, inferred: dict[str, object]) -> str:
    if _tube_like_radius_info(obj) is not None:
        return "tube_properties"
    if _cylinder_like_radius_info(obj) is not None:
        return "cylinder_properties"

    geometry_kind = classify_geometry_object(obj)
    if geometry_kind == "cylinder":
        return "primitive_cylinder"

    axis_name = str(inferred.get("axis", ""))
    if axis_name and _has_cylindrical_surface_along_axis(obj, axis_name):
        return "cylindrical_surface"

    shape = getattr(obj, "Shape", None)
    # Test stubs and simple runtime objects may only expose a bound box.
    if shape is not None and not getattr(shape, "Faces", None):
        return "bounds_only"

    # FreeCAD often exposes tube/body results as generic features; if the leaf
    # object's bound box is strongly cylinder-like and axis-aligned, keep it as
    # a candidate and let later concentric/material checks decide.
    if shape is not None:
        return "axis_aligned_bounds"

    return "not_supported"


def detect_waveguide_face_geometry(
    *,
    geometry_objects: list,
    simulation_box: dict,
    selected_face: str,
    material_names_by_geometry: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    selected_face = str(selected_face or "").strip()
    axis_info = _FACE_AXIS.get(selected_face)
    if axis_info is None:
        return {
            "status": "unsupported",
            "reason": "invalid_selected_face",
            "selected_face": selected_face,
        }

    axis_name, from_min = axis_info
    face_coordinate = _face_coordinate(simulation_box or {}, selected_face)
    if face_coordinate is None:
        return {
            "status": "unsupported",
            "reason": "missing_simulation_box",
            "selected_face": selected_face,
        }

    tol = 1e-7
    if simulation_box:
        axis_min = _as_float(simulation_box.get(f"{axis_name.upper()}Min"), face_coordinate)
        axis_max = _as_float(simulation_box.get(f"{axis_name.upper()}Max"), face_coordinate)
        tol = max(1e-7, abs(axis_max - axis_min) * 1e-8)

    candidates = []
    inspected = []
    material_names_by_geometry = material_names_by_geometry or {}

    seen_candidates = set()
    for obj, bounds_candidates in _iter_leaf_geometry_objects(geometry_objects):
        for bounds in bounds_candidates:
            name = str(getattr(obj, "Name", "") or "")
            touched_face = _touches_selected_face(bounds, axis_name, face_coordinate, from_min, tol)
            inferred = _inferred_axis_aligned_cylinder(obj, bounds, tol)
            radius_info = None
            support_reason = None
            accepted = False
            rejection_reason = None

            if not touched_face:
                rejection_reason = "does_not_touch_selected_face"
            elif inferred is None:
                rejection_reason = "bounds_not_cylinder_like"
            elif str(inferred["axis"]) != axis_name:
                rejection_reason = f"axis_mismatch:{inferred['axis']}"
            else:
                radius_info = _radius_info_from_object(obj, inferred)
                support_reason = _support_reason_for_cylinder_like_object(obj, inferred)
                if support_reason == "not_supported":
                    rejection_reason = "unsupported_shape_type"
                else:
                    accepted = True

            inspected.append(
                {
                    "geometry_name": name,
                    "bounds": dict(bounds),
                    "touched_selected_face": touched_face,
                    "inferred_axis": None if inferred is None else str(inferred.get("axis", "")),
                    "inferred_radius": None if inferred is None else float(inferred.get("radius", 0.0)),
                    "radius_from_properties": None if not touched_face or inferred is None else dict(radius_info or {}),
                    "support_reason": support_reason,
                    "accepted": accepted,
                    "rejection_reason": rejection_reason,
                    "material_names": list(material_names_by_geometry.get(name, [])),
                }
            )

            if not accepted:
                continue

            key = (
                name,
                round(float(radius_info["radius"]), 9),
                tuple(round(float(value), 9) for value in inferred["center"]),
            )
            if key in seen_candidates:
                continue
            seen_candidates.add(key)
            candidates.append(
                {
                    "geometry_name": name,
                    "radius": float(radius_info["radius"]),
                    "inner_radius": float(radius_info.get("inner_radius", 0.0)),
                    "center": list(inferred["center"]),
                    "radius_source": str(radius_info.get("source", "bounds")),
                    "material_names": list(material_names_by_geometry.get(name, [])),
                }
            )

    if len(candidates) < 2:
        return {
            "status": "unsupported",
            "reason": "insufficient_cylinder_candidates",
            "selected_face": selected_face,
            "axis": axis_name,
            "candidates": sorted(candidates, key=lambda item: item["radius"]),
            "inspected": inspected,
        }

    # Group by transverse center coordinates to find concentric pairs.
    center_groups: dict[tuple[float, float], list[dict[str, object]]] = defaultdict(list)
    group_tolerances: dict[tuple[float, float], float] = {}
    for item in candidates:
        center = _transverse_center(item["center"], axis_name)
        radius = float(item.get("radius", 0.0) or 0.0)
        center_tol = max(tol, max(radius, 1.0) * 2e-3)

        matched_key = None
        for key in center_groups:
            key_tol = group_tolerances.get(key, center_tol)
            if abs(center[0] - key[0]) <= max(center_tol, key_tol) and abs(center[1] - key[1]) <= max(center_tol, key_tol):
                matched_key = key
                break

        if matched_key is None:
            matched_key = center
            group_tolerances[matched_key] = center_tol
        else:
            group_tolerances[matched_key] = max(group_tolerances.get(matched_key, center_tol), center_tol)

        center_groups[matched_key].append(item)

    best_pair = None
    for _, group in center_groups.items():
        if len(group) < 2:
            continue
        by_radius = sorted(group, key=lambda item: float(item["radius"]))
        inner = by_radius[0]
        outer = by_radius[-1]
        if float(outer["radius"]) <= float(inner["radius"]) + tol:
            continue
        best_pair = (inner, outer)
        break

    if best_pair is None:
        return {
            "status": "unsupported",
            "reason": "no_concentric_pair",
            "selected_face": selected_face,
            "axis": axis_name,
            "candidates": sorted(candidates, key=lambda item: item["radius"]),
            "inspected": inspected,
        }

    inner, outer = best_pair
    return {
        "status": "supported",
        "kind": "coax_axis_aligned",
        "selected_face": selected_face,
        "axis": axis_name,
        "inner": inner,
        "outer": outer,
        "candidates": sorted(candidates, key=lambda item: item["radius"]),
        "inspected": inspected,
    }


__all__ = ["detect_waveguide_face_geometry"]