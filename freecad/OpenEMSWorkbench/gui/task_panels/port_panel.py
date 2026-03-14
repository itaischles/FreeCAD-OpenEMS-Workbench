from __future__ import annotations

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel


class PortTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Port"
    FIELDS = [
        {
            "name": "PortType",
            "label": "Port Type",
            "type": "enum",
            "choices": ["Lumped", "Waveguide", "PlaneWave"],
        },
        {"name": "PortNumber", "label": "Port Number", "type": "int"},
        {"name": "Resistance", "label": "Resistance (Ohm)", "type": "float"},
        {"name": "Excite", "label": "Excite", "type": "bool"},
        {
            "name": "PropagationDirection",
            "label": "Propagation Direction",
            "type": "enum",
            "choices": ["+x", "-x", "+y", "-y", "+z", "-z"],
        },
        {"name": "PortStartX", "label": "Port Start X", "type": "float"},
        {"name": "PortStartY", "label": "Port Start Y", "type": "float"},
        {"name": "PortStartZ", "label": "Port Start Z", "type": "float"},
        {"name": "PortStopX", "label": "Port Stop X", "type": "float"},
        {"name": "PortStopY", "label": "Port Stop Y", "type": "float"},
        {"name": "PortStopZ", "label": "Port Stop Z", "type": "float"},
    ]
