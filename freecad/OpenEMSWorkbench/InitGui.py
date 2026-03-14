import os
import traceback

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
        command_names = [
            "OpenEMS_CreateAnalysis",
            "OpenEMS_CreateSimulation",
            "OpenEMS_CreateMaterial",
            "OpenEMS_CreateBoundary",
            "OpenEMS_CreatePort",
            "OpenEMS_CreateGrid",
            "OpenEMS_CreateDumpBox",
            "OpenEMS_SetActiveAnalysis",
            "OpenEMS_AssignSelectedToActiveAnalysis",
            "OpenEMS_EditSelected",
            "OpenEMS_RunPreflight",
            "OpenEMS_ExportDryRun",
            "OpenEMS_RunSimulation",
            "OpenEMS_ShowHideMeshOverlay",
            "OpenEMS_RefreshMeshOverlay",
        ]
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

            command_names = list(WORKBENCH_COMMANDS)

            try:
                register_commands()
            except Exception as exc:
                App.Console.PrintError(
                    f"OpenEMS command registration warning: {exc}\n"
                )
                App.Console.PrintMessage(traceback.format_exc())

            self.appendToolbar("OpenEMS", command_names)
            self.appendMenu("OpenEMS", command_names)
            App.Console.PrintMessage("OpenEMS workbench initialized.\n")
        except Exception as exc:  # pragma: no cover - only exercised in FreeCAD GUI
            # Keep menu visibility even when optional command imports fail.
            try:
                self.appendToolbar("OpenEMS", command_names)
                self.appendMenu("OpenEMS", command_names)
                App.Console.PrintError(f"OpenEMS initialization warning: {exc}\n")
                App.Console.PrintMessage(traceback.format_exc())
            except Exception as inner_exc:
                App.Console.PrintError(f"OpenEMS initialization failed: {inner_exc}\n")
                App.Console.PrintMessage(traceback.format_exc())

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(OpenEMSWorkbench())
