from __future__ import annotations

import os

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except ImportError:  # pragma: no cover - only in FreeCAD runtime
    App = None
    Gui = None

try:
    from objects import (
        create_boundary,
        create_dumpbox,
        create_grid,
        create_material,
        create_port,
        create_simulation,
    )
except ImportError:
    from OpenEMSWorkbench.objects import (
        create_boundary,
        create_dumpbox,
        create_grid,
        create_material,
        create_port,
        create_simulation,
    )


COMMAND_DEFINITIONS = {
    "OpenEMS_CreateSimulation": {
        "menu_text": "Create Simulation",
        "tooltip": "Create an openEMS simulation container object.",
        "factory": create_simulation,
    },
    "OpenEMS_CreateMaterial": {
        "menu_text": "Create Material",
        "tooltip": "Create an openEMS material object.",
        "factory": create_material,
    },
    "OpenEMS_CreateBoundary": {
        "menu_text": "Create Boundary",
        "tooltip": "Create an openEMS boundary object.",
        "factory": create_boundary,
    },
    "OpenEMS_CreatePort": {
        "menu_text": "Create Port",
        "tooltip": "Create an openEMS port object.",
        "factory": create_port,
    },
    "OpenEMS_CreateGrid": {
        "menu_text": "Create Grid",
        "tooltip": "Create an openEMS FDTD grid object.",
        "factory": create_grid,
    },
    "OpenEMS_CreateDumpBox": {
        "menu_text": "Create DumpBox",
        "tooltip": "Create an openEMS dump box object.",
        "factory": create_dumpbox,
    },
}

EDIT_COMMAND_NAME = "OpenEMS_EditSelected"


def _command_icon() -> str:
    if App is None:
        return ""
    return os.path.join(
        App.getUserAppDataDir(),
        "Mod",
        "OpenEMSWorkbench",
        "resources",
        "icons",
        "OpenEMSWorkbench.svg",
    )


class _CreateObjectCommand:
    def __init__(self, command_name: str):
        self.command_name = command_name

    def GetResources(self):
        data = COMMAND_DEFINITIONS[self.command_name]
        return {
            "MenuText": data["menu_text"],
            "ToolTip": data["tooltip"],
            "Pixmap": _command_icon(),
        }

    def Activated(self):
        if App is None:
            return

        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        data = COMMAND_DEFINITIONS[self.command_name]
        try:
            data["factory"](doc)
            App.Console.PrintMessage(f"OpenEMS: Created {data['menu_text']}.\n")
        except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
            App.Console.PrintError(f"OpenEMS: Failed to create object: {exc}\n")

    def IsActive(self):
        return App is not None and App.ActiveDocument is not None


class _EditSelectedObjectCommand:
    def GetResources(self):
        return {
            "MenuText": "Edit Selected OpenEMS Object",
            "ToolTip": "Open the task panel for the selected OpenEMS object.",
            "Pixmap": _command_icon(),
        }

    def Activated(self):
        if App is None or Gui is None:
            return
        if App.ActiveDocument is None or Gui.ActiveDocument is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        selection = Gui.Selection.getSelection()
        if len(selection) != 1:
            App.Console.PrintError("OpenEMS: Select exactly one OpenEMS object to edit.\n")
            return

        selected = selection[0]
        proxy = getattr(selected, "Proxy", None)
        proxy_type = getattr(proxy, "TYPE", "")
        if not str(proxy_type).startswith("OpenEMS_"):
            App.Console.PrintError("OpenEMS: Selected object is not an OpenEMS object.\n")
            return

        try:
            from gui.task_panels import create_panel_for_object
        except ImportError:
            from OpenEMSWorkbench.gui.task_panels import create_panel_for_object

        panel = create_panel_for_object(selected)
        if panel is None:
            App.Console.PrintError("OpenEMS: No task panel registered for selected object.\n")
            return

        try:
            if hasattr(selected, "ViewObject") and selected.ViewObject is not None:
                opened = False
                vp_proxy = getattr(selected.ViewObject, "Proxy", None)
                if vp_proxy is not None and hasattr(vp_proxy, "setEdit"):
                    opened = bool(Gui.ActiveDocument.setEdit(selected.Name))

                if not opened:
                    Gui.Control.showDialog(panel)
                    App.Console.PrintMessage("OpenEMS: Opened task panel directly.\n")
            else:
                Gui.Control.showDialog(panel)
                App.Console.PrintMessage("OpenEMS: Opened task panel directly.\n")
        except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
            App.Console.PrintError(f"OpenEMS: Failed to open task panel: {exc}\n")

    def IsActive(self):
        if App is None or Gui is None:
            return False
        if App.ActiveDocument is None:
            return False
        return len(Gui.Selection.getSelection()) == 1


def register_object_commands() -> list[str]:
    if Gui is None:
        return []

    registered = []
    for command_name in COMMAND_DEFINITIONS:
        if command_name not in Gui.listCommands():
            Gui.addCommand(command_name, _CreateObjectCommand(command_name))
        registered.append(command_name)

    if EDIT_COMMAND_NAME not in Gui.listCommands():
        Gui.addCommand(EDIT_COMMAND_NAME, _EditSelectedObjectCommand())
    registered.append(EDIT_COMMAND_NAME)
    return registered


WORKBENCH_OBJECT_COMMANDS = [
    "OpenEMS_CreateSimulation",
    "OpenEMS_CreateMaterial",
    "OpenEMS_CreateBoundary",
    "OpenEMS_CreatePort",
    "OpenEMS_CreateGrid",
    "OpenEMS_CreateDumpBox",
    EDIT_COMMAND_NAME,
]