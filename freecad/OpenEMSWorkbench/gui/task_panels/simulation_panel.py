from __future__ import annotations

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel


class SimulationTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Simulation"
    FIELDS = [
        {"name": "SolverName", "label": "Solver Name", "type": "string"},
        {
            "name": "CoordinateSystem",
            "label": "Coordinate System",
            "type": "enum",
            "choices": ["Cartesian", "Cylindrical"],
        },
        {"name": "DeltaUnit", "label": "Delta Unit (m)", "type": "float"},
        {"name": "NumberOfTimeSteps", "label": "Number Of Time Steps", "type": "int"},
        {"name": "EndCriteria", "label": "End Criteria", "type": "float"},
        {"name": "OutputDirectory", "label": "Output Directory", "type": "string"},
        {"name": "SolverExecutable", "label": "Solver Executable", "type": "string"},
        {"name": "SolverArguments", "label": "Solver Arguments", "type": "string"},
        {"name": "RunBlocking", "label": "Run Blocking", "type": "bool"},
    ]
