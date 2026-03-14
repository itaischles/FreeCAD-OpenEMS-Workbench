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


def read_analysis_for_export(analysis) -> dict:
    members = collect_members(analysis)

    simulation = members.simulations[0] if members.simulations else None
    grid = members.grids[0] if members.grids else None
    boundary = members.boundaries[0] if members.boundaries else None

    return {
        "analysis_name": str(getattr(analysis, "Name", "analysis")),
        "simulation": _object_to_dict(
            simulation,
            ["SolverName", "CoordinateSystem", "DeltaUnit", "NumberOfTimeSteps", "EndCriteria", "OutputDirectory"],
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
        "materials": [
            _object_to_dict(m, ["EpsilonR", "MuR", "Kappa", "IsPEC"]) for m in members.materials
        ],
        "ports": [
            _object_to_dict(
                p,
                ["PortType", "PortNumber", "Resistance", "Excite", "PropagationDirection"],
            )
            for p in sorted(members.ports, key=lambda item: int(getattr(item, "PortNumber", 0)))
        ],
        "dumpboxes": [
            _object_to_dict(d, ["DumpType", "Enabled", "FrequencySpec"]) for d in members.dumpboxes
        ],
        "geometry_objects": _collect_geometry_objects(analysis),
    }
