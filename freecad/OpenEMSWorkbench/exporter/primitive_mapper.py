from __future__ import annotations

try:
    from exporter.model import GeometryEntry
except ImportError:
    from OpenEMSWorkbench.exporter.model import GeometryEntry


def _map_box(obj) -> GeometryEntry:
    shape = getattr(obj, "Shape", None)
    if shape is not None and hasattr(shape, "BoundBox"):
        bb = shape.BoundBox
        params = {
            "start": [float(bb.XMin), float(bb.YMin), float(bb.ZMin)],
            "stop": [float(bb.XMax), float(bb.YMax), float(bb.ZMax)],
        }
    else:
        length = float(getattr(obj, "Length", 1.0))
        width = float(getattr(obj, "Width", 1.0))
        height = float(getattr(obj, "Height", 1.0))
        params = {
            "start": [0.0, 0.0, 0.0],
            "stop": [length, width, height],
        }

    return GeometryEntry(
        object_name=str(getattr(obj, "Name", "")),
        object_label=str(getattr(obj, "Label", getattr(obj, "Name", ""))),
        primitive="box",
        params=params,
    )


def _map_cylinder(obj) -> GeometryEntry:
    radius = float(getattr(obj, "Radius", 1.0))
    height = float(getattr(obj, "Height", 1.0))
    base = [0.0, 0.0, 0.0]

    placement = getattr(obj, "Placement", None)
    if placement is not None and hasattr(placement, "Base"):
        base = [
            float(getattr(placement.Base, "x", 0.0)),
            float(getattr(placement.Base, "y", 0.0)),
            float(getattr(placement.Base, "z", 0.0)),
        ]

    return GeometryEntry(
        object_name=str(getattr(obj, "Name", "")),
        object_label=str(getattr(obj, "Label", getattr(obj, "Name", ""))),
        primitive="cylinder",
        params={
            "base": base,
            "radius": radius,
            "height": height,
            "axis": "z",
        },
    )


def map_primitive_geometry(obj, geometry_kind: str) -> GeometryEntry:
    if geometry_kind == "box":
        return _map_box(obj)
    if geometry_kind == "cylinder":
        return _map_cylinder(obj)
    raise ValueError(f"Unsupported primitive kind: {geometry_kind}")
