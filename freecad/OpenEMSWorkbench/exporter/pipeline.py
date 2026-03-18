from __future__ import annotations

from pathlib import Path
import struct

try:
    from exporter.document_reader import read_analysis_for_export
    from exporter.geometry_classifier import classify_geometry_object
    from exporter.model import ExportModel
    from exporter.primitive_mapper import map_primitive_geometry
    from exporter.script_generator import generate_openems_script
    from exporter.stl_fallback import export_as_stl_entry
except ImportError:
    from OpenEMSWorkbench.exporter.document_reader import read_analysis_for_export
    from OpenEMSWorkbench.exporter.geometry_classifier import classify_geometry_object
    from OpenEMSWorkbench.exporter.model import ExportModel
    from OpenEMSWorkbench.exporter.primitive_mapper import map_primitive_geometry
    from OpenEMSWorkbench.exporter.script_generator import generate_openems_script
    from OpenEMSWorkbench.exporter.stl_fallback import export_as_stl_entry

try:
    from meshing import build_mesh_for_analysis
except ImportError:
    from OpenEMSWorkbench.meshing import build_mesh_for_analysis

try:
    from utils.export_paths import build_export_paths, ensure_export_dirs
except ImportError:
    from OpenEMSWorkbench.utils.export_paths import build_export_paths, ensure_export_dirs


def _build_assignment_lookup(extracted: dict) -> dict[str, dict[str, int | str]]:
    lookup: dict[str, dict[str, int | str]] = {}
    for item in extracted.get("material_assignments", []):
        geometry_name = str(item.get("geometry_name", "")).strip()
        if not geometry_name:
            continue

        material_name = str(item.get("material_name", "")).strip()
        priority = int(item.get("priority", 0) or 0)
        assignment = {
            "material_name": material_name,
            "priority": priority,
        }

        existing = lookup.get(geometry_name)
        if existing is not None and existing != assignment:
            raise ValueError(
                f"Geometry '{geometry_name}' has multiple material assignments in export handoff"
            )

        lookup[geometry_name] = assignment

    return lookup


def _mesh_lines_to_dict(mesh) -> dict:
    return {
        "coordinate_system": str(getattr(mesh, "coordinate_system", "Cartesian") or "Cartesian"),
        "x": [float(value) for value in getattr(mesh, "x", ())],
        "y": [float(value) for value in getattr(mesh, "y", ())],
        "z": [float(value) for value in getattr(mesh, "z", ())],
        "radial": [float(value) for value in getattr(mesh, "radial", ())],
        "azimuth": [float(value) for value in getattr(mesh, "azimuth", ())],
    }


def _polyhedron_geometries(model: ExportModel) -> list:
    return [geo for geo in model.geometries if getattr(geo, "primitive", "") == "polyhedron"]


def _stl_path_for_geometry(geo) -> Path:
    path_text = str(
        getattr(getattr(geo, "stl_artifact", None), "path", "")
        or geo.params.get("stl_path", "")
    ).strip()
    return Path(path_text)


def _looks_like_ascii_stl(header: bytes, trailer: bytes) -> bool:
    return header.lstrip().lower().startswith(b"solid") and b"endsolid" in trailer.lower()


def _looks_like_binary_stl(path: Path) -> bool:
    size = path.stat().st_size
    if size < 84:
        return False
    with path.open("rb") as handle:
        handle.seek(80)
        triangle_count = struct.unpack("<I", handle.read(4))[0]
    expected_size = 84 + triangle_count * 50
    return expected_size == size


def _validate_stl_artifact(geo) -> None:
    stl_path = _stl_path_for_geometry(geo)
    if not str(stl_path):
        raise ValueError(f"STL-backed geometry '{geo.object_name}' does not define an STL file path.")
    if not stl_path.exists() or not stl_path.is_file():
        raise ValueError(f"STL-backed geometry '{geo.object_name}' is missing its STL file: {stl_path}")
    if stl_path.stat().st_size <= 0:
        raise ValueError(f"STL-backed geometry '{geo.object_name}' has an empty STL file: {stl_path}")

    with stl_path.open("rb") as handle:
        header = handle.read(256)
        handle.seek(max(stl_path.stat().st_size - 256, 0))
        trailer = handle.read(256)

    if _looks_like_ascii_stl(header, trailer):
        return
    if _looks_like_binary_stl(stl_path):
        return

    raise ValueError(
        f"STL-backed geometry '{geo.object_name}' produced an invalid STL artifact that is neither valid ASCII STL nor valid binary STL: {stl_path}"
    )


def _validate_stl_fallback_geometries(model: ExportModel, *, runnable: bool) -> None:
    polyhedrons = _polyhedron_geometries(model)
    if not polyhedrons:
        return

    for geo in polyhedrons:
        _validate_stl_artifact(geo)

    if not runnable:
        return

    executable = str((model.simulation or {}).get("SolverExecutable") or "").strip()
    if not executable:
        raise ValueError(
            "Runnable export with STL-backed geometry requires SolverExecutable to be configured so STL-reader support can be validated."
        )

    try:
        try:
            from execution.runtime_discovery import inspect_python_runtime
        except ImportError:
            from OpenEMSWorkbench.execution.runtime_discovery import inspect_python_runtime
    except Exception as exc:
        raise ValueError(f"Failed to load runtime capability checks for STL-backed geometry: {exc}") from exc

    runtime_result = inspect_python_runtime(executable)
    if not runtime_result.ok:
        raise ValueError(
            "Runnable export with STL-backed geometry requires a Python runtime with openEMS/CSXCAD modules. "
            f"Runtime check failed for '{executable}': {runtime_result.message}"
        )

    if not bool(runtime_result.capabilities.get("stl_reader", False)):
        raise ValueError(
            "Selected Python runtime does not expose the CSXCAD STL reader required for STL-backed geometry. "
            f"Runtime '{executable}' reported: {runtime_result.message}"
        )


def _build_export_model(extracted: dict, stl_dir: Path, analysis=None) -> ExportModel:
    assignment_lookup = _build_assignment_lookup(extracted)
    mesh_lines = {}
    if analysis is not None:
        _, _, mesh = build_mesh_for_analysis(analysis)
        mesh_lines = _mesh_lines_to_dict(mesh)

    model = ExportModel(
        analysis_name=extracted["analysis_name"],
        simulation=extracted["simulation"],
        grid=extracted["grid"],
        simulation_box=extracted.get("simulation_box", {}),
        mesh_lines=mesh_lines,
        materials=extracted["materials"],
        boundary=extracted["boundary"],
        ports=extracted["ports"],
        dumpboxes=extracted["dumpboxes"],
        geometries=[],
    )

    for obj in extracted["geometry_objects"]:
        geometry_kind = classify_geometry_object(obj)
        if geometry_kind in {"box", "cylinder"}:
            entry = map_primitive_geometry(obj, geometry_kind)
        else:
            entry = export_as_stl_entry(obj, stl_dir)

        assignment = assignment_lookup.get(entry.object_name)
        if assignment is not None:
            entry.assigned_material_name = str(assignment["material_name"])
            entry.assignment_priority = int(assignment["priority"])

        model.geometries.append(entry)

    return model


def _result_dict(paths: dict, model: ExportModel, run_output_dir: Path | None = None) -> dict:
    result = {
        "paths": {k: str(v) for k, v in paths.items()},
        "analysis": model.analysis_name,
        "geometry_count": len(model.geometries),
        "primitive_count": sum(1 for g in model.geometries if g.primitive in {"box", "cylinder"}),
        "stl_count": sum(1 for g in model.geometries if g.primitive == "polyhedron"),
    }
    if run_output_dir is not None:
        result["run_output_dir"] = str(run_output_dir)
    return result


def export_analysis_dry_run(analysis, base_output_dir: str | Path, document_name: str) -> dict:
    extracted = read_analysis_for_export(analysis)
    paths = build_export_paths(base_output_dir, document_name, extracted["analysis_name"])
    ensure_export_dirs(paths)
    model = _build_export_model(extracted, paths["stl_dir"], analysis=analysis)
    _validate_stl_fallback_geometries(model, runnable=False)
    generate_openems_script(model, paths["script"], runnable=False)
    return _result_dict(paths, model)


def export_analysis_run_ready(
    analysis,
    base_output_dir: str | Path,
    document_name: str,
    run_output_dir: str | Path | None = None,
) -> dict:
    extracted = read_analysis_for_export(analysis)
    paths = build_export_paths(base_output_dir, document_name, extracted["analysis_name"])
    ensure_export_dirs(paths)

    run_dir = Path(run_output_dir) if run_output_dir else paths["run_dir"]
    run_dir.mkdir(parents=True, exist_ok=True)

    model = _build_export_model(extracted, paths["stl_dir"], analysis=analysis)
    _validate_stl_fallback_geometries(model, runnable=True)
    generate_openems_script(
        model,
        paths["script"],
        runnable=True,
        run_output_dir=run_dir,
    )
    return _result_dict(paths, model, run_output_dir=run_dir)
