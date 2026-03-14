from __future__ import annotations

import os

TOOLTIP = "Workbench scaffold for openEMS FDTD model setup"

COMMAND_NAME = "OpenEMS_Placeholder"

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except ImportError:  # pragma: no cover - exercised only inside FreeCAD
    App = None
    Gui = None

try:
    from commands.object_commands import register_object_commands
except ImportError:
    from OpenEMSWorkbench.commands.object_commands import register_object_commands


WORKBENCH_COMMANDS = [
    "OpenEMS_CreateSimulation",
    "OpenEMS_CreateMaterial",
    "OpenEMS_CreateBoundary",
    "OpenEMS_CreatePort",
    "OpenEMS_CreateGrid",
    "OpenEMS_CreateDumpBox",
    COMMAND_NAME,
]


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


class _PlaceholderCommand:
    def GetResources(self):
        return {
            "MenuText": "OpenEMS Placeholder",
            "ToolTip": TOOLTIP,
            "Pixmap": _command_icon(),
        }

    def Activated(self):
        if App is not None:
            App.Console.PrintMessage(
                "OpenEMS workbench scaffold loaded successfully.\n"
            )

    def IsActive(self):
        return True


def register_commands():
    if Gui is None:
        return []
    created = register_object_commands()
    if COMMAND_NAME not in Gui.listCommands():
        Gui.addCommand(COMMAND_NAME, _PlaceholderCommand())
    if COMMAND_NAME not in created:
        created.append(COMMAND_NAME)
    return created
