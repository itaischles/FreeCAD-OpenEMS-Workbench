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
        create_analysis,
        create_boundary,
        create_dumpbox,
        create_grid,
        create_material,
        create_port,
        create_simulation,
    )
except ImportError:
    from OpenEMSWorkbench.objects import (
        create_analysis,
        create_boundary,
        create_dumpbox,
        create_grid,
        create_material,
        create_port,
        create_simulation,
    )

try:
    from utils.analysis_context import (
        assign_members_to_analysis_detailed,
        get_active_analysis,
        get_analyses,
        get_proxy_type,
        set_active_analysis,
    )
except ImportError:
    from OpenEMSWorkbench.utils.analysis_context import (
        assign_members_to_analysis_detailed,
        get_active_analysis,
        get_analyses,
        get_proxy_type,
        set_active_analysis,
    )

try:
    from validation import format_findings, run_preflight, summarize_findings
except ImportError:
    from OpenEMSWorkbench.validation import format_findings, run_preflight, summarize_findings


COMMAND_DEFINITIONS = {
    "OpenEMS_CreateAnalysis": {
        "menu_text": "Create Analysis",
        "tooltip": "Create an openEMS analysis ownership container.",
        "factory": create_analysis,
    },
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
SET_ACTIVE_ANALYSIS_COMMAND = "OpenEMS_SetActiveAnalysis"
ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND = "OpenEMS_AssignSelectedToActiveAnalysis"
RUN_PREFLIGHT_COMMAND = "OpenEMS_RunPreflight"


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


class _SetActiveAnalysisCommand:
    def GetResources(self):
        return {
            "MenuText": "Set Active Analysis",
            "ToolTip": "Set selected OpenEMS Analysis as active.",
            "Pixmap": _command_icon(),
        }

    def Activated(self):
        if App is None or Gui is None:
            return
        if App.ActiveDocument is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        selection = Gui.Selection.getSelection()
        if len(selection) != 1:
            App.Console.PrintError("OpenEMS: Select exactly one Analysis object.\n")
            return

        selected = selection[0]
        if get_proxy_type(selected) != "OpenEMS_Analysis":
            App.Console.PrintError("OpenEMS: Selected object is not an Analysis object.\n")
            return

        set_active_analysis(App.ActiveDocument, selected)
        App.ActiveDocument.recompute()
        App.Console.PrintMessage(f"OpenEMS: Active analysis set to '{selected.Label}'.\n")

    def IsActive(self):
        return App is not None and Gui is not None and App.ActiveDocument is not None


class _AssignSelectedToActiveAnalysisCommand:
    def GetResources(self):
        return {
            "MenuText": "Assign Selected To Active Analysis",
            "ToolTip": "Add selected OpenEMS objects to the active analysis group.",
            "Pixmap": _command_icon(),
        }

    def Activated(self):
        if App is None or Gui is None:
            return
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        analysis = get_active_analysis(doc)
        if analysis is None:
            App.Console.PrintError("OpenEMS: No active analysis found. Create one first.\n")
            return

        selection = Gui.Selection.getSelection()
        if not selection:
            App.Console.PrintError("OpenEMS: Select one or more OpenEMS objects to assign.\n")
            return

        details = assign_members_to_analysis_detailed(analysis, selection)
        doc.recompute()
        App.Console.PrintMessage(
            "OpenEMS: Assignment result for "
            f"'{analysis.Label}': added={details['added']}, "
            f"already_member={details['already_member']}, ignored={details['ignored']}.\n"
        )

    def IsActive(self):
        return App is not None and Gui is not None and App.ActiveDocument is not None


class _RunPreflightCommand:
    def GetResources(self):
        return {
            "MenuText": "Run Preflight",
            "ToolTip": "Run OpenEMS analysis preflight validation checks.",
            "Pixmap": _command_icon(),
        }

    def Activated(self):
        if App is None:
            return
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        analysis = get_active_analysis(doc)
        if analysis is None:
            analyses = get_analyses(doc)
            if len(analyses) == 1:
                analysis = analyses[0]
            else:
                App.Console.PrintError("OpenEMS: No active analysis found.\n")
                return

        findings = run_preflight(analysis)
        for line in format_findings(findings):
            App.Console.PrintMessage(f"OpenEMS Preflight: {line}\n")

        summary = summarize_findings(findings)
        if not summary["ok"]:
            App.Console.PrintError("OpenEMS: Preflight failed (errors present).\n")
        else:
            App.Console.PrintMessage("OpenEMS: Preflight passed.\n")

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

    if EDIT_COMMAND_NAME not in Gui.listCommands():
        Gui.addCommand(EDIT_COMMAND_NAME, _EditSelectedObjectCommand())
    registered.append(EDIT_COMMAND_NAME)

    if SET_ACTIVE_ANALYSIS_COMMAND not in Gui.listCommands():
        Gui.addCommand(SET_ACTIVE_ANALYSIS_COMMAND, _SetActiveAnalysisCommand())
    registered.append(SET_ACTIVE_ANALYSIS_COMMAND)

    if ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND not in Gui.listCommands():
        Gui.addCommand(
            ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND,
            _AssignSelectedToActiveAnalysisCommand(),
        )
    registered.append(ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND)

    if RUN_PREFLIGHT_COMMAND not in Gui.listCommands():
        Gui.addCommand(RUN_PREFLIGHT_COMMAND, _RunPreflightCommand())
    registered.append(RUN_PREFLIGHT_COMMAND)
    return registered


WORKBENCH_OBJECT_COMMANDS = [
    "OpenEMS_CreateAnalysis",
    "OpenEMS_CreateSimulation",
    "OpenEMS_CreateMaterial",
    "OpenEMS_CreateBoundary",
    "OpenEMS_CreatePort",
    "OpenEMS_CreateGrid",
    "OpenEMS_CreateDumpBox",
    SET_ACTIVE_ANALYSIS_COMMAND,
    ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND,
    EDIT_COMMAND_NAME,
    RUN_PREFLIGHT_COMMAND,
]