from __future__ import annotations

try:
    import FreeCAD as App
except ImportError:  # pragma: no cover - FreeCAD runtime only
    App = None

try:
    from utils.analysis_context import get_proxy_type
except ImportError:
    from OpenEMSWorkbench.utils.analysis_context import get_proxy_type

try:
    from model import BOUNDARY_TYPES, DEFAULTS
except ImportError:
    from OpenEMSWorkbench.model import BOUNDARY_TYPES, DEFAULTS

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
        if bool(getattr(obj, "OpenEMSSimulationBox", False)):
            continue
        if hasattr(obj, "Shape"):
            geometry.append(obj)
    geometry.sort(key=lambda o: str(getattr(o, "Name", "")))
    return geometry


def _as_float(value, default: float = 0.0) -> float:
    if hasattr(value, "Value"):
        try:
            return float(value.Value)
        except Exception:
            return float(default)
    try:
        return float(value)
    except Exception:
        return float(default)


def _read_simulation_box_margin(simulation) -> float:
    margin = _as_float(getattr(simulation, "SimulationBoxMargin", 0.0), 0.0)
    return margin if margin >= 0.0 else 0.0


def _shape_bounds(obj) -> dict | None:
    shape = getattr(obj, "Shape", None)
    bb = getattr(shape, "BoundBox", None)
    if bb is None:
        return None
    fields = ["XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax"]
    if not all(hasattr(bb, key) for key in fields):
        return None
    return {
        "xmin": _as_float(bb.XMin),
        "ymin": _as_float(bb.YMin),
        "zmin": _as_float(bb.ZMin),
        "xmax": _as_float(bb.XMax),
        "ymax": _as_float(bb.YMax),
        "zmax": _as_float(bb.ZMax),
    }


def _compute_simulation_box(geometry_objects: list, margin: float) -> dict:
    bounds = [_shape_bounds(obj) for obj in geometry_objects]
    bounds = [entry for entry in bounds if entry is not None]
    if not bounds:
        return {}

    xmin = min(item["xmin"] for item in bounds) - margin
    ymin = min(item["ymin"] for item in bounds) - margin
    zmin = min(item["zmin"] for item in bounds) - margin
    xmax = max(item["xmax"] for item in bounds) + margin
    ymax = max(item["ymax"] for item in bounds) + margin
    zmax = max(item["zmax"] for item in bounds) + margin

    return {
        "XMin": xmin,
        "YMin": ymin,
        "ZMin": zmin,
        "XMax": xmax,
        "YMax": ymax,
        "ZMax": zmax,
        "Start": [xmin, ymin, zmin],
        "Stop": [xmax, ymax, zmax],
        "Size": [xmax - xmin, ymax - ymin, zmax - zmin],
        "Margin": margin,
        "Source": "auto",
    }


def _find_simulation_box_object(analysis):
    for obj in list(getattr(analysis, "Group", [])):
        if bool(getattr(obj, "OpenEMSSimulationBox", False)):
            return obj

    # Fallback: recover an existing helper box already in the document but not yet in Group.
    document = getattr(analysis, "Document", None)
    if document is not None:
        for obj in list(getattr(document, "Objects", [])):
            if bool(getattr(obj, "OpenEMSSimulationBox", False)):
                return obj
    return None


def _mark_simulation_box(obj):
    if hasattr(obj, "addProperty") and not hasattr(obj, "OpenEMSSimulationBox"):
        try:
            obj.addProperty(
                "App::PropertyBool",
                "OpenEMSSimulationBox",
                "OpenEMS",
                "Marks helper simulation region object so exporter ignores it as user geometry.",
            )
        except Exception:
            pass
    try:
        obj.OpenEMSSimulationBox = True
    except Exception:
        pass


def _ensure_simulation_box_view_defaults(obj) -> None:
    # Apply display defaults once so users can still customize afterwards.
    if hasattr(obj, "addProperty") and not hasattr(obj, "OpenEMSViewDefaultsApplied"):
        try:
            obj.addProperty(
                "App::PropertyBool",
                "OpenEMSViewDefaultsApplied",
                "OpenEMS",
                "Tracks whether default simulation-box view style was initialized.",
            )
        except Exception:
            pass

    if bool(getattr(obj, "OpenEMSViewDefaultsApplied", False)):
        return

    view_obj = getattr(obj, "ViewObject", None)
    if view_obj is not None:
        try:
            view_obj.Transparency = 80
        except Exception:
            pass

    try:
        obj.OpenEMSViewDefaultsApplied = True
    except Exception:
        pass


def _ensure_box_boundary_properties(obj) -> None:
    face_defaults = {
        "BoundaryXMin": DEFAULTS["boundary"]["xmin"],
        "BoundaryXMax": DEFAULTS["boundary"]["xmax"],
        "BoundaryYMin": DEFAULTS["boundary"]["ymin"],
        "BoundaryYMax": DEFAULTS["boundary"]["ymax"],
        "BoundaryZMin": DEFAULTS["boundary"]["zmin"],
        "BoundaryZMax": DEFAULTS["boundary"]["zmax"],
    }

    if hasattr(obj, "addProperty"):
        for prop_name in face_defaults:
            if hasattr(obj, prop_name):
                continue
            try:
                obj.addProperty(
                    "App::PropertyEnumeration",
                    prop_name,
                    "OpenEMS Boundary",
                    "Boundary condition assigned to simulation-box face.",
                )
            except Exception:
                pass

    for prop_name, default_value in face_defaults.items():
        if not hasattr(obj, prop_name):
            continue
        try:
            current = str(getattr(obj, prop_name, "") or "")
            setattr(obj, prop_name, BOUNDARY_TYPES)
            if current in BOUNDARY_TYPES:
                setattr(obj, prop_name, current)
            else:
                setattr(obj, prop_name, default_value)
        except Exception:
            pass

    if hasattr(obj, "addProperty") and not hasattr(obj, "BoundaryPMLCells"):
        try:
            obj.addProperty(
                "App::PropertyInteger",
                "BoundaryPMLCells",
                "OpenEMS Boundary",
                "Number of PML cells used with PML boundary conditions.",
            )
        except Exception:
            pass

    if hasattr(obj, "BoundaryPMLCells"):
        try:
            value = int(getattr(obj, "BoundaryPMLCells", DEFAULTS["boundary"]["pml_cells"]) or 0)
            if value < 1:
                value = int(DEFAULTS["boundary"]["pml_cells"])
            obj.BoundaryPMLCells = value
        except Exception:
            pass


def _ensure_margin_property(obj, initial_margin: float = 0.0) -> None:
    if hasattr(obj, "addProperty") and not hasattr(obj, "Margin"):
        try:
            obj.addProperty(
                "App::PropertyLength",
                "Margin",
                "OpenEMS",
                "Margin applied around analysis geometry when simulation box auto-fits on analysis refresh events.",
            )
        except Exception:
            pass

    if hasattr(obj, "Margin"):
        current = _as_float(getattr(obj, "Margin", None), initial_margin)
        if current < 0.0:
            current = 0.0
        try:
            obj.Margin = float(current)
        except Exception:
            pass


def ensure_simulation_box_properties(obj, default_margin: float = 0.0) -> None:
    _mark_simulation_box(obj)
    _ensure_margin_property(obj, initial_margin=default_margin)
    _ensure_box_boundary_properties(obj)


def read_simulation_box_boundary_settings(obj) -> dict:
    if obj is None:
        return {}

    return {
        "XMin": str(getattr(obj, "BoundaryXMin", DEFAULTS["boundary"]["xmin"]) or DEFAULTS["boundary"]["xmin"]),
        "XMax": str(getattr(obj, "BoundaryXMax", DEFAULTS["boundary"]["xmax"]) or DEFAULTS["boundary"]["xmax"]),
        "YMin": str(getattr(obj, "BoundaryYMin", DEFAULTS["boundary"]["ymin"]) or DEFAULTS["boundary"]["ymin"]),
        "YMax": str(getattr(obj, "BoundaryYMax", DEFAULTS["boundary"]["ymax"]) or DEFAULTS["boundary"]["ymax"]),
        "ZMin": str(getattr(obj, "BoundaryZMin", DEFAULTS["boundary"]["zmin"]) or DEFAULTS["boundary"]["zmin"]),
        "ZMax": str(getattr(obj, "BoundaryZMax", DEFAULTS["boundary"]["zmax"]) or DEFAULTS["boundary"]["zmax"]),
        "PMLCells": int(getattr(obj, "BoundaryPMLCells", DEFAULTS["boundary"]["pml_cells"]) or DEFAULTS["boundary"]["pml_cells"]),
    }


def _resolve_boundary_for_export(analysis, legacy_boundary) -> dict:
    box_obj = _find_simulation_box_object(analysis)
    if box_obj is not None:
        ensure_simulation_box_properties(box_obj)
        return read_simulation_box_boundary_settings(box_obj)

    if legacy_boundary is None:
        return {}

    return _object_to_dict(
        legacy_boundary,
        ["XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax", "PMLCells"],
    )


def _read_margin_from_box(box_obj, default_margin: float = 0.0) -> float:
    if box_obj is None or not hasattr(box_obj, "Margin"):
        return max(0.0, _as_float(default_margin, 0.0))

    return max(0.0, _as_float(getattr(box_obj, "Margin", default_margin), 0.0))


def _sync_visible_simulation_box(analysis, simulation_box: dict) -> None:
    if not simulation_box:
        return

    document = getattr(analysis, "Document", None)
    if document is None or not hasattr(document, "addObject"):
        return

    box_obj = _find_simulation_box_object(analysis)
    if box_obj is None:
        try:
            box_obj = document.addObject("Part::Box", "OpenEMSSimulationBox")
        except Exception:
            return

    _mark_simulation_box(box_obj)
    _ensure_simulation_box_view_defaults(box_obj)
    box_obj.Label = "openEMS Simulation Box"
    ensure_simulation_box_properties(
        box_obj,
        default_margin=_as_float(simulation_box.get("Margin", 0.0), 0.0),
    )

    size = simulation_box.get("Size", [0.0, 0.0, 0.0])
    start = simulation_box.get("Start", [0.0, 0.0, 0.0])

    try:
        box_obj.Length = max(_as_float(size[0]), 1e-9)
        box_obj.Width = max(_as_float(size[1]), 1e-9)
        box_obj.Height = max(_as_float(size[2]), 1e-9)
    except Exception:
        return

    if App is not None and hasattr(box_obj, "Placement") and hasattr(App, "Vector"):
        try:
            box_obj.Placement.Base = App.Vector(
                _as_float(start[0]),
                _as_float(start[1]),
                _as_float(start[2]),
            )
        except Exception:
            pass

    if hasattr(analysis, "addObject") and box_obj not in list(getattr(analysis, "Group", [])):
        try:
            setattr(analysis, "_openems_skip_group_refresh", True)
            analysis.addObject(box_obj)
        except Exception:
            pass
        finally:
            try:
                setattr(analysis, "_openems_skip_group_refresh", False)
            except Exception:
                pass


def refresh_simulation_box_for_analysis(analysis) -> dict:
    members = collect_members(analysis)
    simulation = members.simulations[0] if members.simulations else None
    box_obj = _find_simulation_box_object(analysis)

    # Backward-compatible default: simulation property value (typically 0) seeds box margin.
    default_margin = _read_simulation_box_margin(simulation)
    if box_obj is not None:
        _ensure_margin_property(box_obj, initial_margin=default_margin)

    margin = _read_margin_from_box(box_obj, default_margin)
    geometry_objects = _collect_geometry_objects(analysis)
    simulation_box = _compute_simulation_box(geometry_objects, margin)
    _sync_visible_simulation_box(analysis, simulation_box)
    return simulation_box


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
    legacy_boundary = members.boundaries[0] if members.boundaries else None
    material_entries = [_material_to_dict(m) for m in members.materials]
    geometry_objects = _collect_geometry_objects(analysis)
    simulation_box = refresh_simulation_box_for_analysis(analysis)
    boundary = _resolve_boundary_for_export(analysis, legacy_boundary)
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
                "SimulationBoxMargin",
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
        "simulation_box": simulation_box,
        "grid": _object_to_dict(
            grid,
            ["CoordinateSystem", "BaseResolution", "MaxResolution", "GradingFactor", "AutoSmooth"],
        )
        if grid is not None
        else {},
        "boundary": boundary,
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
        "geometry_objects": geometry_objects,
    }
