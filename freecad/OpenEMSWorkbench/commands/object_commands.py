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


def register_object_commands() -> list[str]:
    if Gui is None:
        return []

    registered = []
    for command_name in COMMAND_DEFINITIONS:
        if command_name not in Gui.listCommands():
            Gui.addCommand(command_name, _CreateObjectCommand(command_name))
        registered.append(command_name)
    return registered