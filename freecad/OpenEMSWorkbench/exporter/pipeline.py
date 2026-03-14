from __future__ import annotations

from dataclasses import asdict
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


def export_analysis_dry_run(analysis, base_output_dir: str | Path, document_name: str) -> dict:
    extracted = read_analysis_for_export(analysis)
    paths = build_export_paths(base_output_dir, document_name, extracted["analysis_name"])
    ensure_export_dirs(paths)

    model = ExportModel(
        analysis_name=extracted["analysis_name"],
        simulation=extracted["simulation"],
        grid=extracted["grid"],
        materials=extracted["materials"],
        boundary=extracted["boundary"],
        ports=extracted["ports"],
        dumpboxes=extracted["dumpboxes"],
        geometries=[],
    )

    for obj in extracted["geometry_objects"]:
        geometry_kind = classify_geometry_object(obj)
        if geometry_kind in {"box", "cylinder"}:
            model.geometries.append(map_primitive_geometry(obj, geometry_kind))
        else:
            model.geometries.append(export_as_stl_entry(obj, paths["stl_dir"]))

    generate_openems_script(model, paths["script"])

    return {
        "paths": {k: str(v) for k, v in paths.items()},
        "analysis": model.analysis_name,
        "geometry_count": len(model.geometries),
        "primitive_count": sum(1 for g in model.geometries if g.primitive in {"box", "cylinder"}),
        "stl_count": sum(1 for g in model.geometries if g.primitive == "polyhedron"),
    }
