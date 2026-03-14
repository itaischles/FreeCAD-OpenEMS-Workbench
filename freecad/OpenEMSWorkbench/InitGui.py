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
        all_commands = []
        toolbar_commands = []
        menu_groups = []
        try:
            try:
                from commands.workbench_commands import (
                    WORKBENCH_COMMANDS,
                    WORKBENCH_MENU,
                    WORKBENCH_TOOLBAR,
                    register_commands,
                )
            except ImportError:
                from OpenEMSWorkbench.commands.workbench_commands import (
                    WORKBENCH_COMMANDS,
                    WORKBENCH_MENU,
                    WORKBENCH_TOOLBAR,
                    register_commands,
                )

            all_commands = list(WORKBENCH_COMMANDS)
            toolbar_commands = list(WORKBENCH_TOOLBAR)
            menu_groups = [(name, list(commands)) for name, commands in WORKBENCH_MENU]

            registered = set(all_commands)
            try:
                registered = set(register_commands())
            except Exception as exc:
                App.Console.PrintError(
                    f"OpenEMS command registration warning: {exc}\n"
                )
                App.Console.PrintMessage(traceback.format_exc())

            active_toolbar = [cmd for cmd in toolbar_commands if cmd in registered]
            if active_toolbar:
                self.appendToolbar("OpenEMS", active_toolbar)

            for group_name, group_commands in menu_groups:
                active_group = [cmd for cmd in group_commands if cmd in registered]
                if active_group:
                    self.appendMenu(["OpenEMS", group_name], active_group)

            App.Console.PrintMessage("OpenEMS workbench initialized.\n")
        except Exception as exc:  # pragma: no cover - only exercised in FreeCAD GUI
            # Keep menu visibility even when optional command imports fail.
            try:
                if toolbar_commands:
                    self.appendToolbar("OpenEMS", toolbar_commands)

                for group_name, group_commands in menu_groups:
                    if group_commands:
                        self.appendMenu(["OpenEMS", group_name], group_commands)

                if not toolbar_commands and all_commands:
                    self.appendToolbar("OpenEMS", all_commands)
                if not menu_groups and all_commands:
                    self.appendMenu("OpenEMS", all_commands)

                App.Console.PrintError(f"OpenEMS initialization warning: {exc}\n")
                App.Console.PrintMessage(traceback.format_exc())
            except Exception as inner_exc:
                App.Console.PrintError(f"OpenEMS initialization failed: {inner_exc}\n")
                App.Console.PrintMessage(traceback.format_exc())

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(OpenEMSWorkbench())
