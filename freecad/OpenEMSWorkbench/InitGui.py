import os

import FreeCAD as App
import FreeCADGui as Gui

class OpenEMSWorkbench(Gui.Workbench):
    def __init__(self):
        super().__init__()
        self.__class__.Icon = os.path.join(
            App.getUserAppDataDir(),
            "Mod",
            "OpenEMSWorkbench",
            "resources",
            "icons",
            "OpenEMSWorkbench.svg",
        )
        self.__class__.MenuText = "OpenEMS"
        self.__class__.ToolTip = "Workbench scaffold for openEMS FDTD model setup"

    def Initialize(self):
        try:
            try:
                from commands.workbench_commands import (
                    WORKBENCH_COMMANDS,
                    register_commands,
                )
            except ImportError:
                from OpenEMSWorkbench.commands.workbench_commands import (
                    WORKBENCH_COMMANDS,
                    register_commands,
                )

            register_commands()
            self.appendToolbar("OpenEMS", WORKBENCH_COMMANDS)
            self.appendMenu("OpenEMS", WORKBENCH_COMMANDS)
            App.Console.PrintMessage("OpenEMS workbench initialized.\n")
        except Exception as exc:  # pragma: no cover - only exercised in FreeCAD GUI
            App.Console.PrintError(f"OpenEMS initialization failed: {exc}\n")

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(OpenEMSWorkbench())
