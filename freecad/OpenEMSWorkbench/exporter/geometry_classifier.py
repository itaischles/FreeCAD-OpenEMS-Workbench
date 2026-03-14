from __future__ import annotations


def classify_geometry_object(obj) -> str:
    type_id = str(getattr(obj, "TypeId", ""))
    if "Box" in type_id:
        return "box"
    if "Cylinder" in type_id:
        return "cylinder"

    if all(hasattr(obj, attr) for attr in ["Length", "Width", "Height"]):
        return "box"
    if all(hasattr(obj, attr) for attr in ["Radius", "Height"]):
        return "cylinder"

    return "stl"
