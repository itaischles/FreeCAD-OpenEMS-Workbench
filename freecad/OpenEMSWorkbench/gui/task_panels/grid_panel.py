from __future__ import annotations

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel


class GridTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Grid"
    FIELDS = [
        {
            "name": "CoordinateSystem",
            "label": "Coordinate System",
            "type": "enum",
            "choices": ["Cartesian", "Cylindrical"],
        },
        {"name": "BaseResolution", "label": "Base Resolution", "type": "float"},
        {"name": "MaxResolution", "label": "Max Resolution", "type": "float"},
        {"name": "GradingFactor", "label": "Grading Factor", "type": "float"},
        {"name": "AutoSmooth", "label": "Auto Smooth", "type": "bool"},
    ]
