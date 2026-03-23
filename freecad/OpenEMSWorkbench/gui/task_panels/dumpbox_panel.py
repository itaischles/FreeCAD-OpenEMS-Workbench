from __future__ import annotations

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel


class DumpBoxTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS DumpBox"
    FIELDS = [
        {
            "name": "DumpType",
            "label": "Dump Type",
            "type": "enum",
            "choices": ["EField"],
        },
        {
            "name": "DumpMode",
            "label": "Dump Mode",
            "type": "enum",
            "choices": ["TimeDomain"],
        },
        {
            "name": "PlaneAxis",
            "label": "Dump Plane Axis",
            "type": "enum",
            "choices": ["X", "Y", "Z"],
        },
        {"name": "Enabled", "label": "Enabled", "type": "bool"},
    ]
