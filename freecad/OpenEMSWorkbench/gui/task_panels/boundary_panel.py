from __future__ import annotations

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel


class BoundaryTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Boundary"
    _BC_CHOICES = ["PML_8", "MUR", "PEC", "PMC"]
    FIELDS = [
        {"name": "XMin", "label": "XMin", "type": "enum", "choices": _BC_CHOICES},
        {"name": "XMax", "label": "XMax", "type": "enum", "choices": _BC_CHOICES},
        {"name": "YMin", "label": "YMin", "type": "enum", "choices": _BC_CHOICES},
        {"name": "YMax", "label": "YMax", "type": "enum", "choices": _BC_CHOICES},
        {"name": "ZMin", "label": "ZMin", "type": "enum", "choices": _BC_CHOICES},
        {"name": "ZMax", "label": "ZMax", "type": "enum", "choices": _BC_CHOICES},
        {"name": "PMLCells", "label": "PML Cells", "type": "int"},
    ]
