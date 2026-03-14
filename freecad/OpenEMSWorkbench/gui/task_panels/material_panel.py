from __future__ import annotations

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel


class MaterialTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Material"
    FIELDS = [
        {"name": "EpsilonR", "label": "Epsilon R", "type": "float"},
        {"name": "MuR", "label": "Mu R", "type": "float"},
        {"name": "Kappa", "label": "Kappa (S/m)", "type": "float"},
        {"name": "IsPEC", "label": "Is PEC", "type": "bool"},
    ]
