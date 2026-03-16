from __future__ import annotations

try:
    from utils.analysis_context import get_proxy_type
except ImportError:
    from OpenEMSWorkbench.utils.analysis_context import get_proxy_type

try:
    from validation.member_collection import collect_members
except ImportError:
    from OpenEMSWorkbench.validation.member_collection import collect_members


def _object_to_dict(obj, fields: list[str]) -> dict:
    data = {"name": getattr(obj, "Name", ""), "label": getattr(obj, "Label", "")}
    for field in fields:
        data[field] = getattr(obj, field, None)
    return data


def _collect_geometry_objects(analysis) -> list:
    geometry = []
    for obj in list(getattr(analysis, "Group", [])):
        proxy_type = get_proxy_type(obj)
        if proxy_type.startswith("OpenEMS_"):
            continue
        if hasattr(obj, "Shape"):
            geometry.append(obj)
    geometry.sort(key=lambda o: str(getattr(o, "Name", "")))
    return geometry


def _linked_object_names(value) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []

    names = []
    for item in value:
        name = str(getattr(item, "Name", "")).strip()
        if name:
            names.append(name)
    return sorted(set(names))


def _material_to_dict(material) -> dict:
    data = _object_to_dict(material, ["EpsilonR", "MuR", "Kappa", "IsPEC", "AssignmentPriority"])
    data["AssignmentPriority"] = int(data.get("AssignmentPriority", 0) or 0)
    data["AssignedGeometryNames"] = _linked_object_names(getattr(material, "AssignedGeometry", []))
    return data


def read_analysis_for_export(analysis) -> dict:
    members = collect_members(analysis)

    simulation = members.simulations[0] if members.simulations else None
    grid = members.grids[0] if members.grids else None
    boundary = members.boundaries[0] if members.boundaries else None
    material_entries = [_material_to_dict(m) for m in members.materials]
    material_assignments = []

    for material in material_entries:
        material_name = str(material.get("name", ""))
        priority = int(material.get("AssignmentPriority", 0) or 0)
        for geometry_name in material.get("AssignedGeometryNames", []):
            material_assignments.append(
                {
                    "geometry_name": geometry_name,
                    "material_name": material_name,
                    "priority": priority,
                }
            )

    material_assignments.sort(
        key=lambda item: (item["geometry_name"], item["material_name"])
    )

    return {
        "analysis_name": str(getattr(analysis, "Name", "analysis")),
        "simulation": _object_to_dict(
            simulation,
            [
                "SolverName",
                "CoordinateSystem",
                "DeltaUnit",
                "NumberOfTimeSteps",
                "EndCriteria",
                "ExcitationType",
                "ExcitationF0",
                "ExcitationFc",
                "OutputDirectory",
                "SolverExecutable",
                "SolverArguments",
                "RunBlocking",
            ],
        )
        if simulation is not None
        else {},
        "grid": _object_to_dict(
            grid,
            ["CoordinateSystem", "BaseResolution", "MaxResolution", "GradingFactor", "AutoSmooth"],
        )
        if grid is not None
        else {},
        "boundary": _object_to_dict(
            boundary,
            ["XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax", "PMLCells"],
        )
        if boundary is not None
        else {},
        "materials": material_entries,
        "material_assignments": material_assignments,
        "ports": [
            _object_to_dict(
                p,
                [
                    "PortType",
                    "PortNumber",
                    "Resistance",
                    "Excite",
                    "PropagationDirection",
                    "PortStartX",
                    "PortStartY",
                    "PortStartZ",
                    "PortStopX",
                    "PortStopY",
                    "PortStopZ",
                ],
            )
            for p in sorted(members.ports, key=lambda item: int(getattr(item, "PortNumber", 0)))
        ],
        "dumpboxes": [
            _object_to_dict(d, ["DumpType", "Enabled", "FrequencySpec"]) for d in members.dumpboxes
        ],
        "geometry_objects": _collect_geometry_objects(analysis),
    }
