from __future__ import annotations

try:
    from gui.task_panels.dumpbox_panel import DumpBoxTaskPanel
    from gui.task_panels.grid_panel import GridTaskPanel
    from gui.task_panels.material_panel import MaterialTaskPanel
    from gui.task_panels.port_panel import PortTaskPanel
    from gui.task_panels.simulation_box_panel import SimulationBoxTaskPanel
    from gui.task_panels.simulation_panel import SimulationTaskPanel
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.dumpbox_panel import DumpBoxTaskPanel
    from OpenEMSWorkbench.gui.task_panels.grid_panel import GridTaskPanel
    from OpenEMSWorkbench.gui.task_panels.material_panel import MaterialTaskPanel
    from OpenEMSWorkbench.gui.task_panels.port_panel import PortTaskPanel
    from OpenEMSWorkbench.gui.task_panels.simulation_box_panel import SimulationBoxTaskPanel
    from OpenEMSWorkbench.gui.task_panels.simulation_panel import SimulationTaskPanel


PANEL_BY_PROXY_TYPE = {
    "OpenEMS_Simulation": SimulationTaskPanel,
    "OpenEMS_Material": MaterialTaskPanel,
    "OpenEMS_Port": PortTaskPanel,
    "OpenEMS_Grid": GridTaskPanel,
    "OpenEMS_DumpBox": DumpBoxTaskPanel,
}


def get_panel_class_for_object(obj):
    if bool(getattr(obj, "OpenEMSSimulationBox", False)):
        return SimulationBoxTaskPanel

    proxy = getattr(obj, "Proxy", None)
    proxy_type = getattr(proxy, "TYPE", None)
    return PANEL_BY_PROXY_TYPE.get(proxy_type)


def create_panel_for_object(obj):
    panel_class = get_panel_class_for_object(obj)
    if panel_class is None:
        return None
    return panel_class(obj)
