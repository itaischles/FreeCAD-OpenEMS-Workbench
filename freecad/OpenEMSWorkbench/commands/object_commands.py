from __future__ import annotations

import os
import sys

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
        create_dumpbox,
        create_grid,
        create_material,
        create_port,
        create_simulation,
    )
except ImportError:
    from OpenEMSWorkbench.objects import (
        create_analysis,
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
    from model import BOUNDARY_TYPES
except ImportError:
    from OpenEMSWorkbench.model import BOUNDARY_TYPES

try:
    from exporter import export_analysis_dry_run
except ImportError:
    from OpenEMSWorkbench.exporter import export_analysis_dry_run

try:
    from exporter.document_reader import ensure_simulation_box_properties
except ImportError:
    from OpenEMSWorkbench.exporter.document_reader import ensure_simulation_box_properties

try:
    from meshing import MeshResolutionError, build_mesh_for_active_analysis
except ImportError:
    from OpenEMSWorkbench.meshing import MeshResolutionError, build_mesh_for_active_analysis

try:
    from utils.runtime_settings import get_saved_solver_executable, set_saved_solver_executable
except ImportError:
    from OpenEMSWorkbench.utils.runtime_settings import (
        get_saved_solver_executable,
        set_saved_solver_executable,
    )

try:
    from utils.runtime_settings import (
        get_saved_openems_install_dir,
        set_saved_openems_install_dir,
    )
except ImportError:
    from OpenEMSWorkbench.utils.runtime_settings import (
        get_saved_openems_install_dir,
        set_saved_openems_install_dir,
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
ASSIGN_BOUNDARY_TO_SELECTED_FACE_COMMAND = "OpenEMS_AssignBoundaryToSelectedFace"
RUN_PREFLIGHT_COMMAND = "OpenEMS_RunPreflight"
EXPORT_DRY_RUN_COMMAND = "OpenEMS_ExportDryRun"
RUN_SIMULATION_COMMAND = "OpenEMS_RunSimulation"
VALIDATE_RUNTIME_COMMAND = "OpenEMS_ValidateRuntime"
CONFIGURE_RUNTIME_COMMAND = "OpenEMS_ConfigureRuntime"

COMMAND_ICON_FILES = {
    EDIT_COMMAND_NAME: "command-edit-selected.svg",
    SET_ACTIVE_ANALYSIS_COMMAND: "command-set-active-analysis.svg",
    ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND: "command-assign-selected.svg",
    ASSIGN_BOUNDARY_TO_SELECTED_FACE_COMMAND: "command-create-boundary.svg",
    RUN_PREFLIGHT_COMMAND: "command-run-preflight.svg",
    EXPORT_DRY_RUN_COMMAND: "command-export-dry-run.svg",
    RUN_SIMULATION_COMMAND: "command-run-simulation.svg",
    VALIDATE_RUNTIME_COMMAND: "command-validate-runtime.svg",
    CONFIGURE_RUNTIME_COMMAND: "command-configure-runtime.svg",
}

CREATE_COMMANDS = list(COMMAND_DEFINITIONS.keys())
ANALYSIS_COMMANDS = [
    SET_ACTIVE_ANALYSIS_COMMAND,
    ASSIGN_TO_ACTIVE_ANALYSIS_COMMAND,
    ASSIGN_BOUNDARY_TO_SELECTED_FACE_COMMAND,
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

WORKBENCH_TOOLBAR_COMMANDS = [
    "OpenEMS_CreateAnalysis",
    "OpenEMS_CreateSimulation",
    "OpenEMS_CreateMaterial",
    "OpenEMS_CreatePort",
    "OpenEMS_CreateGrid",
    RUN_PREFLIGHT_COMMAND,
    EXPORT_DRY_RUN_COMMAND,
    RUN_SIMULATION_COMMAND,
]

WORKBENCH_MENU_GROUPS = [
    ("Create", CREATE_COMMANDS),
    ("Analysis", ANALYSIS_COMMANDS),
    ("Run", RUN_COMMANDS),
    ("Runtime", RUNTIME_COMMANDS),
]

WORKBENCH_OBJECT_COMMANDS = (
    CREATE_COMMANDS
    + ANALYSIS_COMMANDS
    + RUN_COMMANDS
    + RUNTIME_COMMANDS
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


def _stderr_severity(line: str) -> str:
    text = str(line or "").strip().lower()
    if not text:
        return "info"
    if any(token in text for token in ("fatal", "traceback", "exception", "error:")):
        return "error"
    if "warning" in text:
        return "warning"
    return "info"


def _mesh_cap_summary(grid, mesh) -> str:
    configured = getattr(grid, "MeshPreviewLineCap", None)
    effective = getattr(mesh, "preview_line_cap", None)
    return f"cap_configured={configured}, cap_effective={effective}"


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


def _is_simulation_box_object(obj) -> bool:
    return bool(getattr(obj, "OpenEMSSimulationBox", False))


def _coord(value, lower_name: str, upper_name: str):
    if value is None:
        return None
    if hasattr(value, lower_name):
        return float(getattr(value, lower_name))
    if hasattr(value, upper_name):
        return float(getattr(value, upper_name))
    return None


def _boundary_property_for_selected_face(box_obj, face_name: str, face_obj=None) -> str | None:
    bb = getattr(getattr(box_obj, "Shape", None), "BoundBox", None)
    cm = getattr(face_obj, "CenterOfMass", None)

    if bb is not None and cm is not None:
        x = _coord(cm, "x", "X")
        y = _coord(cm, "y", "Y")
        z = _coord(cm, "z", "Z")
        if x is not None and y is not None and z is not None:
            distances = {
                "BoundaryXMin": abs(x - float(bb.XMin)),
                "BoundaryXMax": abs(x - float(bb.XMax)),
                "BoundaryYMin": abs(y - float(bb.YMin)),
                "BoundaryYMax": abs(y - float(bb.YMax)),
                "BoundaryZMin": abs(z - float(bb.ZMin)),
                "BoundaryZMax": abs(z - float(bb.ZMax)),
            }
            return min(distances, key=distances.get)

    fallback = {
        "Face1": "BoundaryZMin",
        "Face2": "BoundaryZMax",
        "Face3": "BoundaryYMin",
        "Face4": "BoundaryYMax",
        "Face5": "BoundaryXMin",
        "Face6": "BoundaryXMax",
    }
    return fallback.get(str(face_name))


def _resolve_export_base(analysis) -> str:
    simulation = _analysis_simulation(analysis)
    configured = str(getattr(simulation, "OutputDirectory", "") or "").strip() if simulation else ""
    if configured:
        return os.path.abspath(configured)

    return os.path.join(
        App.getUserAppDataDir(),
        "Mod",
        "OpenEMSWorkbench",
        "exports",
    )


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


class _AssignBoundaryToSelectedFaceCommand:
    def GetResources(self):
        return {
            "MenuText": "Assign Boundary To Face",
            "ToolTip": "Assign boundary condition to selected simulation-box face(s).",
            "Pixmap": _command_icon(ASSIGN_BOUNDARY_TO_SELECTED_FACE_COMMAND),
        }

    def Activated(self):
        if App is None or Gui is None:
            return
        if QtWidgets is None:
            App.Console.PrintError("OpenEMS: Qt runtime is unavailable for boundary selection.\n")
            return
        doc = App.ActiveDocument
        if doc is None:
            App.Console.PrintError("OpenEMS: No active document. Create a document first.\n")
            return

        selection_ex = Gui.Selection.getSelectionEx() or []
        if not selection_ex:
            App.Console.PrintError("OpenEMS: Select one or more simulation-box faces first.\n")
            return

        boundary_type, ok = QtWidgets.QInputDialog.getItem(
            None,
            "Assign Boundary To Face",
            "Boundary type:",
            BOUNDARY_TYPES,
            0,
            False,
        )
        if not ok:
            App.Console.PrintMessage("OpenEMS: Boundary face assignment canceled.\n")
            return

        changed = 0
        skipped = 0
        touched_objects = set()

        for item in selection_ex:
            box_obj = getattr(item, "Object", None)
            if not _is_simulation_box_object(box_obj):
                skipped += 1
                continue

            ensure_simulation_box_properties(box_obj)

            names = list(getattr(item, "SubElementNames", []) or [])
            subobjs = list(getattr(item, "SubObjects", []) or [])
            face_pairs = []
            for idx, name in enumerate(names):
                if str(name).startswith("Face"):
                    face_obj = subobjs[idx] if idx < len(subobjs) else None
                    face_pairs.append((name, face_obj))

            if not face_pairs:
                skipped += 1
                continue

            for face_name, face_obj in face_pairs:
                prop_name = _boundary_property_for_selected_face(box_obj, face_name, face_obj)
                if not prop_name or not hasattr(box_obj, prop_name):
                    skipped += 1
                    continue
                setattr(box_obj, prop_name, str(boundary_type))
                changed += 1
                touched_objects.add(getattr(box_obj, "Name", "box"))

        if changed:
            doc.recompute()
            App.Console.PrintMessage(
                "OpenEMS: Assigned boundary "
                f"'{boundary_type}' to {changed} face(s) on {len(touched_objects)} simulation box object(s).\n"
            )
        else:
            App.Console.PrintError(
                "OpenEMS: No simulation-box faces were updated. "
                "Select simulation box faces and try again.\n"
            )

        if skipped:
            App.Console.PrintMessage(f"OpenEMS: Skipped {skipped} selection item(s).\n")

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
            App.Console.PrintError(
                "OpenEMS: Preflight has errors, but continuing dry-run export.\n"
            )
            for line in format_findings(findings):
                App.Console.PrintMessage(f"OpenEMS Preflight: {line}\n")
        elif summary.get("warnings", 0):
            for line in format_findings(findings):
                App.Console.PrintMessage(f"OpenEMS Preflight: {line}\n")

        export_base = _resolve_export_base(analysis)

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

        export_base = _resolve_export_base(analysis)

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
            if Gui is not None:
                try:
                    Gui.updateGui()
                except Exception:
                    pass

        def _solver_stderr(line: str):
            if not line:
                return
            severity = _stderr_severity(line)
            if severity == "error":
                App.Console.PrintError(f"openEMS: {line}\n")
            elif severity == "warning" and hasattr(App.Console, "PrintWarning"):
                App.Console.PrintWarning(f"openEMS: {line}\n")
            else:
                App.Console.PrintMessage(f"openEMS: {line}\n")
            if Gui is not None:
                try:
                    Gui.updateGui()
                except Exception:
                    pass

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
        elif result.status == "launched":
            App.Console.PrintMessage(f"OpenEMS: {result.message}\n")
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

        initial = get_saved_openems_install_dir() or r"C:\openEMS"
        selected = QtWidgets.QFileDialog.getExistingDirectory(
            None,
            "Select openEMS Installation Folder",
            initial,
            QtWidgets.QFileDialog.ShowDirsOnly,
        )
        selected = str(selected or "").strip()
        if not selected:
            App.Console.PrintMessage("OpenEMS: Runtime configuration canceled.\n")
            return
        if not os.path.isdir(selected):
            App.Console.PrintError(f"OpenEMS: Invalid openEMS folder: {selected}\n")
            return

        try:
            try:
                from execution.runtime_discovery import discover_python_runtime
            except ImportError:
                from OpenEMSWorkbench.execution.runtime_discovery import discover_python_runtime
        except Exception as exc:
            App.Console.PrintError(f"OpenEMS: Failed to load runtime validator: {exc}\n")
            return

        os.environ["OPENEMS_INSTALL_DIR"] = selected
        os.environ["OPENEMS_INSTALL_PATH"] = selected

        preferred_candidates = [
            sys.executable,
            os.path.join(os.path.dirname(sys.executable), "python.exe"),
            os.path.join(sys.prefix, "python.exe"),
            get_saved_solver_executable(),
        ]
        result = discover_python_runtime(preferred_candidates=preferred_candidates)
        if not result.ok:
            checked = " | ".join(result.checked[-3:]) if result.checked else ""
            suffix = f" Checked: {checked}" if checked else ""
            App.Console.PrintError(
                "OpenEMS: Could not auto-detect a Python interpreter with openEMS/CSXCAD modules "
                f"for installation folder '{selected}'. {result.message}{suffix}\n"
            )
            return

        set_saved_openems_install_dir(selected)
        set_saved_solver_executable(result.executable)
        App.Console.PrintMessage(f"OpenEMS: Saved openEMS installation folder: {selected}\n")
        App.Console.PrintMessage(f"OpenEMS: Auto-detected Python runtime: {result.executable}\n")

        doc = App.ActiveDocument
        if doc is None:
            return
        analysis = _active_or_single_analysis(doc)
        simulation = _analysis_simulation(analysis)
        if simulation is not None:
            simulation.SolverExecutable = result.executable
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
        if ASSIGN_BOUNDARY_TO_SELECTED_FACE_COMMAND not in Gui.listCommands():
            Gui.addCommand(
                ASSIGN_BOUNDARY_TO_SELECTED_FACE_COMMAND,
                _AssignBoundaryToSelectedFaceCommand(),
            )
        registered.append(ASSIGN_BOUNDARY_TO_SELECTED_FACE_COMMAND)
    except Exception as exc:  # pragma: no cover - FreeCAD runtime behavior
        if App is not None:
            App.Console.PrintError(
                f"OpenEMS: Failed to register command '{ASSIGN_BOUNDARY_TO_SELECTED_FACE_COMMAND}': {exc}\n"
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

    return registered
