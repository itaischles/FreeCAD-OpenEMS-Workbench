from __future__ import annotations

from pathlib import Path

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


def _build_export_model(extracted: dict, stl_dir: Path) -> ExportModel:
    assignment_lookup = _build_assignment_lookup(extracted)

    model = ExportModel(
        analysis_name=extracted["analysis_name"],
        simulation=extracted["simulation"],
        grid=extracted["grid"],
        simulation_box=extracted.get("simulation_box", {}),
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
    model = _build_export_model(extracted, paths["stl_dir"])
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

    model = _build_export_model(extracted, paths["stl_dir"])
    generate_openems_script(
        model,
        paths["script"],
        runnable=True,
        run_output_dir=run_dir,
    )
    return _result_dict(paths, model, run_output_dir=run_dir)
