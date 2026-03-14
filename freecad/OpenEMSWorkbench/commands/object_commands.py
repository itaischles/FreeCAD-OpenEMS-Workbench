from __future__ import annotations

import os

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except ImportError:  # pragma: no cover - only in FreeCAD runtime
    App = None
    Gui = None

try:
    from PySide2 import QtWidgets
except Exception:  # pragma: no cover - FreeCAD runtime only
    QtWidgets = None

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

try:
    from utils.runtime_settings import get_saved_solver_executable, set_saved_solver_executable
except ImportError:
    from OpenEMSWorkbench.utils.runtime_settings import (
        get_saved_solver_executable,
        set_saved_solver_executable,
    )


COMMAND_DEFINITIONS = {
    "OpenEMS_CreateAnalysis": {
        "menu_text": "Create Analysis",
        "tooltip": "Create an openEMS analysis ownership container.",
        "icon": "command-create-analysis.svg",
        "factory": create_analysis,
    },
    "OpenEMS_CreateSimulation": {
        "menu_text": "Create Simulation",
        "tooltip": "Create an openEMS simulation container object.",
        "icon": "command-create-simulation.svg",
        "factory": create_simulation,
    },
    "OpenEMS_CreateMaterial": {
        "menu_text": "Create Material",
        "tooltip": "Create an openEMS material object.",
        "icon": "command-create-material.svg",
        "factory": create_material,
    },
    "OpenEMS_CreateBoundary": {
        "menu_text": "Create Boundary",
        "tooltip": "Create an openEMS boundary object.",
        "icon": "command-create-boundary.svg",
        "factory": create_boundary,
    },
    "OpenEMS_CreatePort": {
        "menu_text": "Create Port",
        "tooltip": "Create an openEMS port object.",
        "icon": "command-create-port.svg",
        "factory": create_port,
    },
    "OpenEMS_CreateGrid": {
        "menu_text": "Create Grid",
        "tooltip": "Create an openEMS FDTD grid object.",
        "icon": "command-create-grid.svg",
        "factory": create_grid,
    },
    "OpenEMS_CreateDumpBox": {
        "menu_text": "Create DumpBox",
        "tooltip": "Create an openEMS dump box object.",
        "icon": "command-create-dumpbox.svg",
        "factory": create_dumpbox,
    },
}

EDIT_COMMAND_NAME = "OpenEMS_EditSelected"
SET_ACTIVE_ANALYSIS_COMMAND = "OpenEMS_SetActiveAnalysis"
ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND = "OpenEMS_AssignSelectedToActiveAnalysis"
RUN_PREFLIGHT_COMMAND = "OpenEMS_RunPreflight"
EXPORT_DRY_RUN_COMMAND = "OpenEMS_ExportDryRun"
RUN_SIMULATION_COMMAND = "OpenEMS_RunSimulation"
VALIDATE_RUNTIME_COMMAND = "OpenEMS_ValidateRuntime"
CONFIGURE_RUNTIME_COMMAND = "OpenEMS_ConfigureRuntime"
SHOW_HIDE_MESH_OVERLAY_COMMAND = "OpenEMS_ShowHideMeshOverlay"
REFRESH_MESH_OVERLAY_COMMAND = "OpenEMS_RefreshMeshOverlay"

COMMAND_ICON_FILES = {
    EDIT_COMMAND_NAME: "command-edit-selected.svg",
    SET_ACTIVE_ANALYSIS_COMMAND: "command-set-active-analysis.svg",
    ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND: "command-assign-selected.svg",
    RUN_PREFLIGHT_COMMAND: "command-run-preflight.svg",
    EXPORT_DRY_RUN_COMMAND: "command-export-dry-run.svg",
    RUN_SIMULATION_COMMAND: "command-run-simulation.svg",
    VALIDATE_RUNTIME_COMMAND: "command-validate-runtime.svg",
    CONFIGURE_RUNTIME_COMMAND: "command-configure-runtime.svg",
    SHOW_HIDE_MESH_OVERLAY_COMMAND: "command-toggle-mesh.svg",
    REFRESH_MESH_OVERLAY_COMMAND: "command-refresh-mesh.svg",
}

CREATE_COMMANDS = list(COMMAND_DEFINITIONS.keys())
ANALYSIS_COMMANDS = [
    SET_ACTIVE_ANALYSIS_COMMAND,
    ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND,
    EDIT_COMMAND_NAME,
]
RUN_COMMANDS = [
    RUN_PREFLIGHT_COMMAND,
    EXPORT_DRY_RUN_COMMAND,
    RUN_SIMULATION_COMMAND,
]
RUNTIME_COMMANDS = [
    VALIDATE_RUNTIME_COMMAND,
    CONFIGURE_RUNTIME_COMMAND,
]
VIEW_COMMANDS = [
    SHOW_HIDE_MESH_OVERLAY_COMMAND,
    REFRESH_MESH_OVERLAY_COMMAND,
]

WORKBENCH_TOOLBAR_COMMANDS = [
    "OpenEMS_CreateAnalysis",
    "OpenEMS_CreateSimulation",
    "OpenEMS_CreateMaterial",
    "OpenEMS_CreatePort",
    "OpenEMS_CreateGrid",
    RUN_PREFLIGHT_COMMAND,
    EXPORT_DRY_RUN_COMMAND,
    RUN_SIMULATION_COMMAND,
    SHOW_HIDE_MESH_OVERLAY_COMMAND,
]

WORKBENCH_MENU_GROUPS = [
    ("Create", CREATE_COMMANDS),
    ("Analysis", ANALYSIS_COMMANDS),
    ("Run", RUN_COMMANDS),
    ("Runtime", RUNTIME_COMMANDS),
    ("View", VIEW_COMMANDS),
]

WORKBENCH_OBJECT_COMMANDS = (
    CREATE_COMMANDS
    + ANALYSIS_COMMANDS
    + RUN_COMMANDS
    + RUNTIME_COMMANDS
    + VIEW_COMMANDS
)


def _command_icon(command_name: str | None = None) -> str:
    if App is None:
        return ""
    icon_name = "OpenEMSWorkbench.svg"
    if command_name in COMMAND_DEFINITIONS:
        icon_name = COMMAND_DEFINITIONS[command_name].get("icon", icon_name)
    elif command_name in COMMAND_ICON_FILES:
        icon_name = COMMAND_ICON_FILES[command_name]

    candidate = os.path.join(
        App.getUserAppDataDir(),
        "Mod",
        "OpenEMSWorkbench",
        "resources",
        "icons",
        icon_name,
    )
    if os.path.isfile(candidate):
        return candidate

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


def _read_log_tail(path: str, max_lines: int = 3) -> str:
    try:
        if not path or not os.path.isfile(path):
            return ""
        text = open(path, "r", encoding="utf-8", errors="replace").read().strip()
        if not text:
            return ""
        lines = text.splitlines()
        return " | ".join(lines[-max_lines:])
    except Exception:
        return ""


def _preflight_gate(analysis):
    findings = run_preflight(analysis)
    summary = summarize_findings(findings)
    return summary["ok"], findings, summary


def _active_or_single_analysis(doc):
    analysis = get_active_analysis(doc)
    if analysis is not None:
        return analysis
    analyses = get_analyses(doc)
    if len(analyses) == 1:
        return analyses[0]
    return None


def _analysis_simulation(analysis):
    if analysis is None:
        return None
    for member in list(getattr(analysis, "Group", [])):
        if get_proxy_type(member) == "OpenEMS_Simulation":
            return member
    return None


class _CreateObjectCommand:
    def __init__(self, command_name: str):
        self.command_name = command_name

    def GetResources(self):
        data = COMMAND_DEFINITIONS[self.command_name]
        return {
            "MenuText": data["menu_text"],
            "ToolTip": data["tooltip"],
            "Pixmap": _command_icon(self.command_name),
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
            "MenuText": "Edit Selected",
            "ToolTip": "Open the task panel for the selected OpenEMS object.",
            "Pixmap": _command_icon(EDIT_COMMAND_NAME),
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
            "Pixmap": _command_icon(SET_ACTIVE_ANALYSIS_COMMAND),
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
            "MenuText": "Assign Selected",
            "ToolTip": "Add selected OpenEMS objects to the active analysis group.",
            "Pixmap": _command_icon(ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND),
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
            "Pixmap": _command_icon(RUN_PREFLIGHT_COMMAND),
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
            "MenuText": "Export Dry Run",
            "ToolTip": "Run preflight and generate openEMS script plus geometry artifacts.",
            "Pixmap": _command_icon(EXPORT_DRY_RUN_COMMAND),
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
            "MenuText": "Toggle Mesh Overlay",
            "ToolTip": "Toggle viewport mesh overlay generated from active analysis grid.",
            "Pixmap": _command_icon(SHOW_HIDE_MESH_OVERLAY_COMMAND),
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
            "Pixmap": _command_icon(RUN_SIMULATION_COMMAND),
        }

    def Activated(self):
        if App is None:
            return
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        analysis = _active_or_single_analysis(doc)
        if analysis is None:
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
                from execution import (
                    auto_configure_solver_runtime,
                    run_analysis,
                    validate_configured_solver_runtime,
                )
            except ImportError:
                from OpenEMSWorkbench.execution import (
                    auto_configure_solver_runtime,
                    run_analysis,
                    validate_configured_solver_runtime,
                )
        except Exception as exc:
            App.Console.PrintError(f"OpenEMS: Failed to load execution module: {exc}\n")
            return

        detected_ok, detected_message = auto_configure_solver_runtime(analysis)
        if detected_ok and "Detected Python runtime" in detected_message:
            App.Console.PrintMessage(f"OpenEMS: {detected_message}\n")
            doc.recompute()

        runtime_ok, runtime_message = validate_configured_solver_runtime(analysis)
        if not runtime_ok:
            App.Console.PrintError(f"OpenEMS: Runtime check failed: {runtime_message}\n")
            return
        App.Console.PrintMessage(f"OpenEMS: Runtime check passed. {runtime_message}\n")

        def _solver_stdout(line: str):
            if not line:
                return
            App.Console.PrintMessage(f"openEMS: {line}\n")

        def _solver_stderr(line: str):
            if not line:
                return
            App.Console.PrintError(f"openEMS: {line}\n")

        result = run_analysis(
            analysis,
            export_base,
            str(getattr(doc, "Name", "Document")),
            on_stdout_line=_solver_stdout,
            on_stderr_line=_solver_stderr,
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
                if result.status == "failed":
                    tail = _read_log_tail(result.paths["stderr_log"])
                    if tail:
                        App.Console.PrintError(f"OpenEMS: Stderr tail: {tail}\n")

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
            "Pixmap": _command_icon(REFRESH_MESH_OVERLAY_COMMAND),
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


class _ValidateRuntimeCommand:
    def GetResources(self):
        return {
            "MenuText": "Validate Runtime",
            "ToolTip": "Auto-detect and validate Python runtime for Run Simulation.",
            "Pixmap": _command_icon(VALIDATE_RUNTIME_COMMAND),
        }

    def Activated(self):
        if App is None:
            return
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        analysis = _active_or_single_analysis(doc)
        if analysis is None:
            App.Console.PrintError("OpenEMS: No active analysis found.\n")
            return

        try:
            try:
                from execution import auto_configure_solver_runtime, validate_configured_solver_runtime
            except ImportError:
                from OpenEMSWorkbench.execution import (
                    auto_configure_solver_runtime,
                    validate_configured_solver_runtime,
                )
        except Exception as exc:
            App.Console.PrintError(f"OpenEMS: Failed to load execution module: {exc}\n")
            return

        auto_ok, auto_message = auto_configure_solver_runtime(analysis)
        if auto_ok:
            App.Console.PrintMessage(f"OpenEMS: {auto_message}\n")
            doc.recompute()
        else:
            App.Console.PrintError(f"OpenEMS: Runtime auto-detect failed: {auto_message}\n")

        runtime_ok, runtime_message = validate_configured_solver_runtime(analysis)
        if runtime_ok:
            App.Console.PrintMessage(f"OpenEMS: Runtime validation passed: {runtime_message}\n")
        else:
            App.Console.PrintError(f"OpenEMS: Runtime validation failed: {runtime_message}\n")

    def IsActive(self):
        return App is not None and App.ActiveDocument is not None


class _ConfigureRuntimeCommand:
    def GetResources(self):
        return {
            "MenuText": "Configure Runtime...",
            "ToolTip": "Set and save a default Python runtime for OpenEMS simulations.",
            "Pixmap": _command_icon(CONFIGURE_RUNTIME_COMMAND),
        }

    def Activated(self):
        if App is None:
            return
        if QtWidgets is None:
            App.Console.PrintError("OpenEMS: Qt runtime is unavailable for file selection.\n")
            return

        initial = get_saved_solver_executable()
        selected, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Select Python Runtime for OpenEMS",
            initial,
            "Python executable (python*.exe);;Executable (*.exe);;All files (*)",
        )
        selected = str(selected or "").strip()
        if not selected:
            App.Console.PrintMessage("OpenEMS: Runtime configuration canceled.\n")
            return

        try:
            try:
                from execution.runtime_discovery import validate_python_runtime
            except ImportError:
                from OpenEMSWorkbench.execution.runtime_discovery import validate_python_runtime
        except Exception as exc:
            App.Console.PrintError(f"OpenEMS: Failed to load runtime validator: {exc}\n")
            return

        ok, message = validate_python_runtime(selected)
        if not ok:
            App.Console.PrintError(f"OpenEMS: Runtime validation failed: {message}\n")
            return

        set_saved_solver_executable(selected)
        App.Console.PrintMessage(f"OpenEMS: Saved default runtime: {selected}\n")

        doc = App.ActiveDocument
        if doc is None:
            return
        analysis = _active_or_single_analysis(doc)
        simulation = _analysis_simulation(analysis)
        if simulation is not None:
            simulation.SolverExecutable = selected
            doc.recompute()
            App.Console.PrintMessage(
                f"OpenEMS: Applied runtime to simulation '{getattr(simulation, 'Label', simulation.Name)}'.\n"
            )

    def IsActive(self):
        return App is not None


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
        if VALIDATE_RUNTIME_COMMAND not in Gui.listCommands():
            Gui.addCommand(VALIDATE_RUNTIME_COMMAND, _ValidateRuntimeCommand())
        registered.append(VALIDATE_RUNTIME_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(f"OpenEMS: Failed to register command '{VALIDATE_RUNTIME_COMMAND}': {exc}\n")

    try:
        if CONFIGURE_RUNTIME_COMMAND not in Gui.listCommands():
            Gui.addCommand(CONFIGURE_RUNTIME_COMMAND, _ConfigureRuntimeCommand())
        registered.append(CONFIGURE_RUNTIME_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(f"OpenEMS: Failed to register command '{CONFIGURE_RUNTIME_COMMAND}': {exc}\n")

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
