from __future__ import annotations

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
    from model import BOUNDARY_TYPES
    from exporter.document_reader import ensure_simulation_box_properties
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel
    from OpenEMSWorkbench.model import BOUNDARY_TYPES
    from OpenEMSWorkbench.exporter.document_reader import ensure_simulation_box_properties


class SimulationBoxTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Simulation Box"
    FIELDS = [
        {"name": "BoundaryXMin", "label": "XMin Boundary", "type": "enum", "choices": BOUNDARY_TYPES},
        {"name": "BoundaryXMax", "label": "XMax Boundary", "type": "enum", "choices": BOUNDARY_TYPES},
        {"name": "BoundaryYMin", "label": "YMin Boundary", "type": "enum", "choices": BOUNDARY_TYPES},
        {"name": "BoundaryYMax", "label": "YMax Boundary", "type": "enum", "choices": BOUNDARY_TYPES},
        {"name": "BoundaryZMin", "label": "ZMin Boundary", "type": "enum", "choices": BOUNDARY_TYPES},
        {"name": "BoundaryZMax", "label": "ZMax Boundary", "type": "enum", "choices": BOUNDARY_TYPES},
        {"name": "BoundaryPMLCells", "label": "PML Cells", "type": "int"},
    ]

    def _sync_object_properties(self) -> None:
        try:
            ensure_simulation_box_properties(self.obj)
        except Exception:
            # Keep task panel available even if property sync fails.
            pass
