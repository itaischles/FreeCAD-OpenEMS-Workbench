from __future__ import annotations

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel


class GridTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Grid (Mesh Settings)"
    FIELDS = [
        {
            "name": "CoordinateSystem",
            "label": "Coordinate System",
            "type": "enum",
            "choices": ["Cartesian", "Cylindrical"],
        },
        {"name": "MeshBaseStep", "label": "Mesh Base Step", "type": "float"},
        {"name": "MeshMaxStep", "label": "Mesh Max Step", "type": "float"},
        {"name": "MeshGrowthRate", "label": "Mesh Growth Rate", "type": "float"},
        {"name": "MeshAutoSmooth", "label": "Mesh Auto Smooth", "type": "bool"},
        {"name": "MeshPreviewLineCap", "label": "Mesh Preview Line Cap", "type": "int"},
    ]
