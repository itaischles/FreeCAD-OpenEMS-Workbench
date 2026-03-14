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

try:
    from exporter import export_analysis_dry_run
except ImportError:
    from OpenEMSWorkbench.exporter import export_analysis_dry_run

try:
    from meshing import MeshResolutionError, build_mesh_for_active_analysis
except ImportError:
    from OpenEMSWorkbench.meshing import MeshResolutionError, build_mesh_for_active_analysis

try:
    from visualization import hide_overlay, is_overlay_visible, refresh_overlay, show_overlay
except ImportError:
    from OpenEMSWorkbench.visualization import (
        hide_overlay,
        is_overlay_visible,
        refresh_overlay,
        show_overlay,
    )


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
EXPORT_DRY_RUN_COMMAND = "OpenEMS_ExportDryRun"
RUN_SIMULATION_COMMAND = "OpenEMS_RunSimulation"
SHOW_HIDE_MESH_OVERLAY_COMMAND = "OpenEMS_ShowHideMeshOverlay"
REFRESH_MESH_OVERLAY_COMMAND = "OpenEMS_RefreshMeshOverlay"


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


def _resolve_mesh(doc):
    try:
        _, grid, mesh = build_mesh_for_active_analysis(doc)
        return grid, mesh, None
    except MeshResolutionError as exc:
        return None, None, str(exc)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        return None, None, f"Unexpected mesh resolution error: {exc}"


def _preflight_gate(analysis):
    findings = run_preflight(analysis)
    summary = summarize_findings(findings)
    return summary["ok"], findings, summary


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


class _ExportDryRunCommand:
    def GetResources(self):
        return {
            "MenuText": "Export Dry-Run Script",
            "ToolTip": "Run preflight and generate openEMS script plus geometry artifacts.",
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

        ok, findings, summary = _preflight_gate(analysis)
        if not ok:
            App.Console.PrintError("OpenEMS: Export blocked by preflight errors.\n")
            for line in format_findings(findings):
                App.Console.PrintMessage(f"OpenEMS Preflight: {line}\n")
            return

        export_base = os.path.join(
            App.getUserAppDataDir(),
            "Mod",
            "OpenEMSWorkbench",
            "exports",
        )

        try:
            result = export_analysis_dry_run(analysis, export_base, str(getattr(doc, "Name", "Document")))
            App.Console.PrintMessage("OpenEMS: Dry-run export completed.\n")
            App.Console.PrintMessage(
                "OpenEMS: Export stats "
                f"geometry={result['geometry_count']}, "
                f"primitives={result['primitive_count']}, "
                f"stl={result['stl_count']}.\n"
            )
            App.Console.PrintMessage(f"OpenEMS: Script path {result['paths']['script']}\n")
            App.Console.PrintMessage(f"OpenEMS: STL folder {result['paths']['stl_dir']}\n")
        except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
            App.Console.PrintError(f"OpenEMS: Dry-run export failed: {exc}\n")

    def IsActive(self):
        return App is not None and App.ActiveDocument is not None


class _ShowHideMeshOverlayCommand:
    def GetResources(self):
        return {
            "MenuText": "Show/Hide Mesh Overlay",
            "ToolTip": "Toggle viewport mesh overlay generated from active analysis grid.",
            "Pixmap": _command_icon(),
            "Checkable": True,
        }

    def Activated(self, checked=False):
        _ = checked
        if App is None:
            return
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        if is_overlay_visible():
            _, message = hide_overlay()
            App.Console.PrintMessage(f"{message}\n")
            return

        grid, mesh, error = _resolve_mesh(doc)
        if error is not None:
            App.Console.PrintError(f"OpenEMS: {error}\n")
            return

        _, message = show_overlay(mesh)
        App.Console.PrintMessage(
            f"{message} Grid='{getattr(grid, 'Label', 'openEMS Grid')}'.\n"
        )

    def IsActive(self):
        return App is not None and Gui is not None and App.ActiveDocument is not None

    def IsChecked(self):
        return bool(is_overlay_visible())


class _RunSimulationCommand:
    def GetResources(self):
        return {
            "MenuText": "Run Simulation",
            "ToolTip": "Run preflight, export run-ready script, and execute solver.",
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

        export_base = os.path.join(
            App.getUserAppDataDir(),
            "Mod",
            "OpenEMSWorkbench",
            "exports",
        )

        App.Console.PrintMessage("OpenEMS: Running simulation (blocking mode).\n")
        try:
            try:
                from execution import run_analysis
            except ImportError:
                from OpenEMSWorkbench.execution import run_analysis
        except Exception as exc:
            App.Console.PrintError(f"OpenEMS: Failed to load execution module: {exc}\n")
            return

        result = run_analysis(
            analysis,
            export_base,
            str(getattr(doc, "Name", "Document")),
        )

        if result.status == "blocked":
            App.Console.PrintError("OpenEMS: Run blocked by preflight errors.\n")
            for line in format_findings(result.findings):
                App.Console.PrintMessage(f"OpenEMS Preflight: {line}\n")
            return

        if result.status == "failed":
            App.Console.PrintError(f"OpenEMS: Run failed: {result.message}\n")
            if result.exit_code is not None:
                App.Console.PrintError(f"OpenEMS: Exit code {result.exit_code}\n")
        else:
            App.Console.PrintMessage("OpenEMS: Simulation completed successfully.\n")

        if result.paths:
            if "script" in result.paths:
                App.Console.PrintMessage(f"OpenEMS: Script path {result.paths['script']}\n")
            if "stdout_log" in result.paths:
                App.Console.PrintMessage(f"OpenEMS: Stdout log {result.paths['stdout_log']}\n")
            if "stderr_log" in result.paths:
                App.Console.PrintMessage(f"OpenEMS: Stderr log {result.paths['stderr_log']}\n")

        if result.duration_seconds is not None:
            App.Console.PrintMessage(
                f"OpenEMS: Run time {result.duration_seconds:.2f} s\n"
            )

    def IsActive(self):
        return App is not None and App.ActiveDocument is not None


class _RefreshMeshOverlayCommand:
    def GetResources(self):
        return {
            "MenuText": "Refresh Mesh Overlay",
            "ToolTip": "Regenerate and refresh viewport mesh overlay from active analysis grid.",
            "Pixmap": _command_icon(),
        }

    def Activated(self):
        if App is None:
            return
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        grid, mesh, error = _resolve_mesh(doc)
        if error is not None:
            App.Console.PrintError(f"OpenEMS: {error}\n")
            return

        _, message = refresh_overlay(mesh)
        App.Console.PrintMessage(
            f"{message} Grid='{getattr(grid, 'Label', 'openEMS Grid')}'.\n"
        )

    def IsActive(self):
        return App is not None and Gui is not None and App.ActiveDocument is not None


def register_object_commands() -> list[str]:
    if Gui is None:
        return []

    registered = []
    for command_name in COMMAND_DEFINITIONS:
        try:
            if command_name not in Gui.listCommands():
                Gui.addCommand(command_name, _CreateObjectCommand(command_name))
            registered.append(command_name)
        except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
            if App is not None:
                App.Console.PrintError(
                    f"OpenEMS: Failed to register command '{command_name}': {exc}\n"
                )

    try:
        if EDIT_COMMAND_NAME not in Gui.listCommands():
            Gui.addCommand(EDIT_COMMAND_NAME, _EditSelectedObjectCommand())
        registered.append(EDIT_COMMAND_NAME)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(f"OpenEMS: Failed to register command '{EDIT_COMMAND_NAME}': {exc}\n")

    try:
        if SET_ACTIVE_ANALYSIS_COMMAND not in Gui.listCommands():
            Gui.addCommand(SET_ACTIVE_ANALYSIS_COMMAND, _SetActiveAnalysisCommand())
        registered.append(SET_ACTIVE_ANALYSIS_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(
                f"OpenEMS: Failed to register command '{SET_ACTIVE_ANALYSIS_COMMAND}': {exc}\n"
            )

    try:
        if ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND not in Gui.listCommands():
            Gui.addCommand(
                ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND,
                _AssignSelectedToActiveAnalysisCommand(),
            )
        registered.append(ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(
                f"OpenEMS: Failed to register command '{ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND}': {exc}\n"
            )

    try:
        if RUN_PREFLIGHT_COMMAND not in Gui.listCommands():
            Gui.addCommand(RUN_PREFLIGHT_COMMAND, _RunPreflightCommand())
        registered.append(RUN_PREFLIGHT_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(f"OpenEMS: Failed to register command '{RUN_PREFLIGHT_COMMAND}': {exc}\n")

    try:
        if EXPORT_DRY_RUN_COMMAND not in Gui.listCommands():
            Gui.addCommand(EXPORT_DRY_RUN_COMMAND, _ExportDryRunCommand())
        registered.append(EXPORT_DRY_RUN_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(f"OpenEMS: Failed to register command '{EXPORT_DRY_RUN_COMMAND}': {exc}\n")

    try:
        if RUN_SIMULATION_COMMAND not in Gui.listCommands():
            Gui.addCommand(RUN_SIMULATION_COMMAND, _RunSimulationCommand())
        registered.append(RUN_SIMULATION_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(f"OpenEMS: Failed to register command '{RUN_SIMULATION_COMMAND}': {exc}\n")

    try:
        if SHOW_HIDE_MESH_OVERLAY_COMMAND not in Gui.listCommands():
            Gui.addCommand(SHOW_HIDE_MESH_OVERLAY_COMMAND, _ShowHideMeshOverlayCommand())
        registered.append(SHOW_HIDE_MESH_OVERLAY_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(
                f"OpenEMS: Failed to register command '{SHOW_HIDE_MESH_OVERLAY_COMMAND}': {exc}\n"
            )

    try:
        if REFRESH_MESH_OVERLAY_COMMAND not in Gui.listCommands():
            Gui.addCommand(REFRESH_MESH_OVERLAY_COMMAND, _RefreshMeshOverlayCommand())
        registered.append(REFRESH_MESH_OVERLAY_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(
                f"OpenEMS: Failed to register command '{REFRESH_MESH_OVERLAY_COMMAND}': {exc}\n"
            )
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
    EXPORT_DRY_RUN_COMMAND,
    RUN_SIMULATION_COMMAND,
    SHOW_HIDE_MESH_OVERLAY_COMMAND,
    REFRESH_MESH_OVERLAY_COMMAND,
]