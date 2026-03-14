from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from utils.analysis_context import get_proxy_type
except ImportError:
    from OpenEMSWorkbench.utils.analysis_context import get_proxy_type


@dataclass
class AnalysisMembers:
    analysis: Any
    simulations: list[Any] = field(default_factory=list)
    materials: list[Any] = field(default_factory=list)
    boundaries: list[Any] = field(default_factory=list)
    ports: list[Any] = field(default_factory=list)
    grids: list[Any] = field(default_factory=list)
    dumpboxes: list[Any] = field(default_factory=list)
    unknown: list[Any] = field(default_factory=list)


def collect_members(analysis: Any) -> AnalysisMembers:
    members = AnalysisMembers(analysis=analysis)
    for obj in list(getattr(analysis, "Group", [])):
        proxy_type = get_proxy_type(obj)
        if proxy_type == "OpenEMS_Simulation":
            members.simulations.append(obj)
        elif proxy_type == "OpenEMS_Material":
            members.materials.append(obj)
        elif proxy_type == "OpenEMS_Boundary":
            members.boundaries.append(obj)
        elif proxy_type == "OpenEMS_Port":
            members.ports.append(obj)
        elif proxy_type == "OpenEMS_Grid":
            members.grids.append(obj)
        elif proxy_type == "OpenEMS_DumpBox":
            members.dumpboxes.append(obj)
        else:
            members.unknown.append(obj)
    return members
