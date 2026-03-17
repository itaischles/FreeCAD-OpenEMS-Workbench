from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GeometryEntry:
    object_name: str
    object_label: str
    primitive: str
    params: dict[str, Any] = field(default_factory=dict)
    assigned_material_name: str | None = None
    assignment_priority: int | None = None


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
