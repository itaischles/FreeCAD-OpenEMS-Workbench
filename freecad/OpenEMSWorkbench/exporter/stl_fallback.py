from __future__ import annotations

from pathlib import Path

try:
    from exporter.model import GeometryEntry
except ImportError:
    from OpenEMSWorkbench.exporter.model import GeometryEntry


def _write_placeholder_stl(path: Path) -> None:
    path.write_text(
        "solid placeholder\n"
        "  facet normal 0 0 0\n"
        "    outer loop\n"
        "      vertex 0 0 0\n"
        "      vertex 0 0 0\n"
        "      vertex 0 0 0\n"
        "    endloop\n"
        "  endfacet\n"
        "endsolid placeholder\n",
        encoding="ascii",
    )


def export_as_stl_entry(obj, stl_dir: Path) -> GeometryEntry:
    object_name = str(getattr(obj, "Name", "geometry"))
    object_label = str(getattr(obj, "Label", object_name))
    stl_path = stl_dir / f"{object_name}.stl"

    shape = getattr(obj, "Shape", None)
    if shape is not None and hasattr(shape, "exportStl"):
        shape.exportStl(str(stl_path))
    else:
        _write_placeholder_stl(stl_path)

    return GeometryEntry(
        object_name=object_name,
        object_label=object_label,
        primitive="polyhedron",
        params={"stl_path": str(stl_path)},
    )
