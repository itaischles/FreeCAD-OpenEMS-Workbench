from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StlArtifact:
    path: str
    format: str = "stl"


@dataclass
class GeometryEntry:
    object_name: str
    object_label: str
    primitive: str
    params: dict[str, Any] = field(default_factory=dict)
    assigned_material_name: str | None = None
    assignment_priority: int | None = None
    stl_artifact: StlArtifact | None = None

    def __post_init__(self) -> None:
        if self.stl_artifact is None:
            stl_path = str(self.params.get("stl_path", "") or "").strip()
            if stl_path:
                self.stl_artifact = StlArtifact(path=stl_path)

        if self.stl_artifact is not None and "stl_path" not in self.params:
            self.params["stl_path"] = self.stl_artifact.path


@dataclass
class ExportModel:
    analysis_name: str
    simulation: dict[str, Any]
    grid: dict[str, Any]
    simulation_box: dict[str, Any] = field(default_factory=dict)
    mesh_lines: dict[str, Any] = field(default_factory=dict)
    materials: list[dict[str, Any]] = field(default_factory=list)
    boundary: dict[str, Any] = field(default_factory=dict)
    ports: list[dict[str, Any]] = field(default_factory=list)
    dumpboxes: list[dict[str, Any]] = field(default_factory=list)
    geometries: list[GeometryEntry] = field(default_factory=list)
