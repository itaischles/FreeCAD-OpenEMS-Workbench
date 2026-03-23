from __future__ import annotations

import math

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - runtime only in FreeCAD
    App = None

try:
    from model import COORDINATE_SYSTEMS, DEFAULTS, EXCITATION_TYPES
    from meshing import build_mesh_for_analysis
    from utils.timestep_budget import compute_timestep_budget
    from utils.unit_contract import (
        canonical_delta_unit_meters,
        detect_freecad_unit_contract,
        is_supported_delta_unit,
    )
    from utils.analysis_context import get_proxy_type
    from objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )
except ImportError:
    from OpenEMSWorkbench.model import COORDINATE_SYSTEMS, DEFAULTS, EXCITATION_TYPES
    from OpenEMSWorkbench.meshing import build_mesh_for_analysis
    from OpenEMSWorkbench.utils.timestep_budget import compute_timestep_budget
    from OpenEMSWorkbench.utils.unit_contract import (
        canonical_delta_unit_meters,
        detect_freecad_unit_contract,
        is_supported_delta_unit,
    )
    from OpenEMSWorkbench.utils.analysis_context import get_proxy_type
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )


_MAX_FC_PROPERTY_INTEGER = 2_000_000_000
_HIDDEN_SIMULATION_PROPERTIES = (
    "DeltaUnit",
    "SimulationBoxMargin",
    "MaxSimulationTime",
    "ComputedTimeStep",
    "ComputedNumberOfTimeSteps",
    "ComputedNumberOfTimeStepsRaw",
    "ComputedNumberOfTimeStepsScientific",
    "ComputedLengthUnitName",
    "TimeStepBudgetStatus",
    "TimeStepBudgetLastReportKey",
)


def _as_float(value, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _format_seconds_display(value: float) -> str:
    seconds = _as_float(value, 0.0)
    if not math.isfinite(seconds):
        return "0 sec"
    if seconds == 0.0:
        return "0 sec"
    abs_seconds = abs(seconds)
    if abs_seconds >= 1.0e4 or abs_seconds < 1.0e-3:
        text = f"{seconds:.8e}"
        mantissa, exponent = text.split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{int(exponent)} sec"
    return f"{seconds:.12f}".rstrip("0").rstrip(".") + " sec"


def _refresh_time_display_fields(obj) -> None:
    if hasattr(obj, "MaxSimulationTimeDisplay"):
        try:
            obj.MaxSimulationTimeDisplay = _format_seconds_display(getattr(obj, "MaxSimulationTime", 0.0))
        except Exception:
            pass
    if hasattr(obj, "ComputedTimeStepDisplay"):
        try:
            obj.ComputedTimeStepDisplay = _format_seconds_display(getattr(obj, "ComputedTimeStep", 0.0))
        except Exception:
            pass


def _analysis_for_member(obj):
    document = getattr(obj, "Document", None)
    if document is None:
        return None
    for candidate in list(getattr(document, "Objects", [])):
        if get_proxy_type(candidate) != "OpenEMS_Analysis":
            continue
        if obj in list(getattr(candidate, "Group", [])):
            return candidate
    return None


def _format_int_scientific(value: int) -> str:
    number = int(value)
    if number == 0:
        return "0"
    sign = "-" if number < 0 else ""
    number = abs(number)
    exponent = len(str(number)) - 1
    mantissa = number / (10 ** exponent)
    mantissa_text = f"{mantissa:.6f}".rstrip("0").rstrip(".")
    return f"{sign}{mantissa_text}e{exponent}"


def _min_positive_spacing(values) -> float | None:
    sequence = tuple(values or ())
    if len(sequence) < 2:
        return None
    minimum = None
    for index in range(1, len(sequence)):
        try:
            step = abs(float(sequence[index]) - float(sequence[index - 1]))
        except Exception:
            continue
        if step <= 0.0:
            continue
        if minimum is None or step < minimum:
            minimum = step
    return minimum


def _mesh_spacing_diagnostic(mesh, delta_m_per_unit: float) -> str:
    coordinate_system = str(getattr(mesh, "coordinate_system", "Cartesian") or "Cartesian")
    if coordinate_system == "Cartesian":
        dx = _min_positive_spacing(getattr(mesh, "x", ()))
        dy = _min_positive_spacing(getattr(mesh, "y", ()))
        dz = _min_positive_spacing(getattr(mesh, "z", ()))
        if dx is None or dy is None or dz is None:
            return ""
        return (
            "mesh min steps: "
            f"dx={dx:.6e} unit ({dx * delta_m_per_unit:.6e} m), "
            f"dy={dy:.6e} unit ({dy * delta_m_per_unit:.6e} m), "
            f"dz={dz:.6e} unit ({dz * delta_m_per_unit:.6e} m)"
        )
    if coordinate_system == "Cylindrical":
        dr = _min_positive_spacing(getattr(mesh, "radial", ()))
        dz = _min_positive_spacing(getattr(mesh, "z", ()))
        if dr is None or dz is None:
            return ""
        return (
            "mesh min steps: "
            f"dr={dr:.6e} unit ({dr * delta_m_per_unit:.6e} m), "
            f"dz={dz:.6e} unit ({dz * delta_m_per_unit:.6e} m)"
        )
    return ""


def _report_timestep_status(
    obj,
    message: str,
    *,
    is_error: bool = False,
    event_key: str = "status",
) -> None:
    if App is None:
        return
    console = getattr(App, "Console", None)
    if console is None:
        return
    signature = f"{event_key}|{'error' if is_error else 'info'}|{message}"
    try:
        last_signature = str(getattr(obj, "TimeStepBudgetLastReportKey", "") or "")
    except Exception:
        last_signature = ""
    if signature == last_signature:
        return

    if hasattr(obj, "TimeStepBudgetLastReportKey"):
        try:
            obj.TimeStepBudgetLastReportKey = signature
        except Exception:
            pass

    try:
        if is_error:
            console.PrintWarning(f"OpenEMS timestep budget: {message}\n")
        else:
            console.PrintMessage(f"OpenEMS timestep budget: {message}\n")
    except Exception:
        pass


def recompute_simulation_timestep_budget(obj, *, emit_report: bool = True) -> tuple[bool, str]:
    if obj is None:
        return False, "No simulation object provided."

    t_max = _as_float(getattr(obj, "MaxSimulationTime", 0.0), 0.0)
    if t_max <= 0.0:
        if hasattr(obj, "ComputedTimeStep"):
            obj.ComputedTimeStep = 0.0
        if hasattr(obj, "ComputedNumberOfTimeSteps"):
            obj.ComputedNumberOfTimeSteps = 0
        if hasattr(obj, "ComputedNumberOfTimeStepsRaw"):
            obj.ComputedNumberOfTimeStepsRaw = ""
        if hasattr(obj, "TimeStepBudgetStatus"):
            obj.TimeStepBudgetStatus = "Invalid T_max (must be > 0 sec)."
        _refresh_time_display_fields(obj)
        if emit_report:
            _report_timestep_status(
                obj,
                "Invalid T_max (must be > 0 sec).",
                is_error=True,
                event_key="invalid_tmax",
            )
        return False, "Invalid T_max"

    analysis = _analysis_for_member(obj)
    if analysis is None:
        if hasattr(obj, "ComputedTimeStep"):
            obj.ComputedTimeStep = 0.0
        if hasattr(obj, "ComputedNumberOfTimeSteps"):
            obj.ComputedNumberOfTimeSteps = 0
        if hasattr(obj, "ComputedNumberOfTimeStepsRaw"):
            obj.ComputedNumberOfTimeStepsRaw = ""
        if hasattr(obj, "TimeStepBudgetStatus"):
            obj.TimeStepBudgetStatus = "No analysis context found for timestep computation."
        _refresh_time_display_fields(obj)
        if emit_report:
            _report_timestep_status(
                obj,
                "No analysis context found for timestep computation.",
                is_error=True,
                event_key="missing_analysis",
            )
        return False, "No analysis context"

    try:
        _, _, mesh = build_mesh_for_analysis(analysis)
        unit_name, freecad_delta_unit = detect_freecad_unit_contract()
        delta_unit = _as_float(freecad_delta_unit, canonical_delta_unit_meters())
        if delta_unit <= 0.0:
            delta_unit = _as_float(getattr(obj, "DeltaUnit", canonical_delta_unit_meters()), canonical_delta_unit_meters())
        if emit_report:
            _report_timestep_status(
                obj,
                f"Detected FreeCAD length unit: {unit_name} (delta={delta_unit:.6e} m/unit)",
                is_error=False,
                event_key="unit_contract",
            )
        dt_sec, nr_ts = compute_timestep_budget(
            mesh,
            delta_unit_meters=delta_unit,
            max_time_sec=t_max,
        )
        spacing_diag = _mesh_spacing_diagnostic(mesh, delta_unit)
    except Exception as exc:
        if hasattr(obj, "ComputedTimeStep"):
            obj.ComputedTimeStep = 0.0
        if hasattr(obj, "ComputedNumberOfTimeSteps"):
            obj.ComputedNumberOfTimeSteps = 0
        if hasattr(obj, "ComputedNumberOfTimeStepsRaw"):
            obj.ComputedNumberOfTimeStepsRaw = ""
        if hasattr(obj, "ComputedNumberOfTimeStepsScientific"):
            obj.ComputedNumberOfTimeStepsScientific = ""
        if hasattr(obj, "TimeStepBudgetStatus"):
            obj.TimeStepBudgetStatus = f"Failed to compute timestep budget: {exc}"
        _refresh_time_display_fields(obj)
        if emit_report:
            _report_timestep_status(
                obj,
                f"Failed to compute timestep budget: {exc}",
                is_error=True,
                event_key="compute_exception",
            )
        return False, f"Computation failed: {exc}"

    if not math.isfinite(dt_sec) or dt_sec <= 0.0:
        if hasattr(obj, "ComputedTimeStep"):
            obj.ComputedTimeStep = 0.0
        if hasattr(obj, "ComputedNumberOfTimeSteps"):
            obj.ComputedNumberOfTimeSteps = 0
        if hasattr(obj, "ComputedNumberOfTimeStepsRaw"):
            obj.ComputedNumberOfTimeStepsRaw = ""
        if hasattr(obj, "ComputedNumberOfTimeStepsScientific"):
            obj.ComputedNumberOfTimeStepsScientific = ""
        if hasattr(obj, "TimeStepBudgetStatus"):
            obj.TimeStepBudgetStatus = "Computed dt is not finite and positive."
        _refresh_time_display_fields(obj)
        if emit_report:
            _report_timestep_status(
                obj,
                "Computed dt is not finite and positive.",
                is_error=True,
                event_key="invalid_dt",
            )
        return False, "Invalid dt"

    raw_nr_ts = int(nr_ts)
    clamped_nr_ts = int(max(1, min(raw_nr_ts, _MAX_FC_PROPERTY_INTEGER)))
    if hasattr(obj, "ComputedTimeStep"):
        obj.ComputedTimeStep = float(dt_sec)
    if hasattr(obj, "ComputedNumberOfTimeSteps"):
        obj.ComputedNumberOfTimeSteps = int(clamped_nr_ts)
    if hasattr(obj, "ComputedNumberOfTimeStepsRaw"):
        obj.ComputedNumberOfTimeStepsRaw = str(raw_nr_ts)
    if hasattr(obj, "ComputedNumberOfTimeStepsScientific"):
        obj.ComputedNumberOfTimeStepsScientific = _format_int_scientific(raw_nr_ts)
    if hasattr(obj, "ComputedLengthUnitName"):
        obj.ComputedLengthUnitName = str(unit_name or "")
    if hasattr(obj, "NumberOfTimeSteps"):
        obj.NumberOfTimeSteps = int(clamped_nr_ts)
    if hasattr(obj, "TimeStepBudgetStatus"):
        if raw_nr_ts > _MAX_FC_PROPERTY_INTEGER:
            obj.TimeStepBudgetStatus = (
                "Computed with units from FreeCAD model settings. "
                f"unit={unit_name}, delta={delta_unit:.6e} m/unit, dt={dt_sec:.6e} sec, "
                f"raw NrTS={raw_nr_ts}, clamped to {_MAX_FC_PROPERTY_INTEGER}."
            )
        else:
            obj.TimeStepBudgetStatus = (
                "Computed with units from FreeCAD model settings. "
                f"unit={unit_name}, delta={delta_unit:.6e} m/unit, dt={dt_sec:.6e} sec, NrTS={raw_nr_ts}."
            )
        if spacing_diag:
            obj.TimeStepBudgetStatus = f"{obj.TimeStepBudgetStatus} {spacing_diag}."
        _refresh_time_display_fields(obj)
        if emit_report:
            _report_timestep_status(
                obj,
                obj.TimeStepBudgetStatus,
                is_error=False,
                event_key="computed_status",
            )
    else:
        _refresh_time_display_fields(obj)
    return True, "ok"


class OpenEMSSimulationProxy(FeatureProxyBase):
    TYPE = "OpenEMS_Simulation"

    def _apply_editor_modes(self, obj) -> None:
        set_editor_mode = getattr(obj, "setEditorMode", None)
        if not callable(set_editor_mode):
            return
        for prop_name in _HIDDEN_SIMULATION_PROPERTIES:
            if not hasattr(obj, prop_name):
                continue
            try:
                # FreeCAD editor mode 2 = hidden in Property editor.
                set_editor_mode(prop_name, 2)
            except Exception:
                continue

    def _enforce_delta_unit(self, obj) -> None:
        expected = canonical_delta_unit_meters()
        current = getattr(obj, "DeltaUnit", expected)
        if is_supported_delta_unit(current, expected_delta_unit=expected):
            return
        try:
            obj.DeltaUnit = expected
        except Exception:
            pass

    def ensure_properties(self, obj):
        self._is_syncing_properties = True
        try:
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "SolverName",
            "OpenEMS",
            "Target solver backend.",
            "openEMS",
            )
            add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "CoordinateSystem",
            "OpenEMS",
            "Simulation coordinate system; must match Grid coordinate system.",
            DEFAULTS["simulation"]["coordinate_system"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "DeltaUnit",
            "OpenEMS",
            "Length unit in meters.",
            DEFAULTS["simulation"]["delta_unit"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "SimulationBoxMargin",
            "OpenEMS",
            "Margin added around auto-derived simulation box domain (model units).",
            0.0,
            )
            add_property_if_missing(
            obj,
            "App::PropertyInteger",
            "NumberOfTimeSteps",
            "OpenEMS",
            "Maximum number of FDTD timesteps.",
            DEFAULTS["simulation"]["nr_ts"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "EndCriteria",
            "OpenEMS",
            "Stopping criteria for field energy decay.",
            DEFAULTS["simulation"]["end_criteria"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "ExcitationType",
            "OpenEMS",
            "Excitation waveform type.",
            DEFAULTS["simulation"]["excitation_type"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "ExcitationFMax",
            "OpenEMS",
            "Maximum excitation frequency in Hz.",
            DEFAULTS["simulation"]["excitation_f_max"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "MaxSimulationTime",
            "OpenEMS",
            "Physical maximum simulation time in sec.",
            DEFAULTS["simulation"]["max_simulation_time"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "MaxSimulationTimeDisplay",
            "OpenEMS",
            "Display value for physical maximum simulation time.",
            "",
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "ComputedTimeStep",
            "OpenEMS",
            "Computed stable time step dt in sec.",
            0.0,
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "ComputedTimeStepDisplay",
            "OpenEMS",
            "Display value for computed stable time step dt.",
            "",
            )
            add_property_if_missing(
            obj,
            "App::PropertyInteger",
            "ComputedNumberOfTimeSteps",
            "OpenEMS",
            "Computed timestep budget NrTS from T_max and dt.",
            0,
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "TimeStepBudgetStatus",
            "OpenEMS",
            "Status of dt/NrTS computation from mesh and T_max.",
            "",
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "ComputedNumberOfTimeStepsRaw",
            "OpenEMS",
            "Raw computed NrTS before GUI integer clamping.",
            "",
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "ComputedNumberOfTimeStepsScientific",
            "OpenEMS",
            "Computed NrTS formatted in scientific notation.",
            "",
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "ComputedLengthUnitName",
            "OpenEMS",
            "Detected FreeCAD model length unit name used for dt computation.",
            "",
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "TimeStepBudgetLastReportKey",
            "OpenEMS",
            "Internal key used to suppress duplicate timestep report messages.",
            "",
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "ExcitationF0",
            "OpenEMS",
            "Excitation center frequency in Hz.",
            DEFAULTS["simulation"]["excitation_f0"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "ExcitationFc",
            "OpenEMS",
            "Excitation bandwidth in Hz.",
            DEFAULTS["simulation"]["excitation_fc"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "SinusoidAmplitude",
            "OpenEMS",
            "Sinusoid amplitude.",
            DEFAULTS["simulation"]["sinusoid_amplitude"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "SinusoidFrequency",
            "OpenEMS",
            "Sinusoid frequency in Hz.",
            DEFAULTS["simulation"]["sinusoid_frequency"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "SinusoidPhaseDeg",
            "OpenEMS",
            "Sinusoid phase in degrees.",
            DEFAULTS["simulation"]["sinusoid_phase_deg"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "GaussianAmplitude",
            "OpenEMS",
            "Gaussian pulse amplitude.",
            DEFAULTS["simulation"]["gaussian_amplitude"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "GaussianSigma",
            "OpenEMS",
            "Gaussian sigma in sec.",
            DEFAULTS["simulation"]["gaussian_sigma"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "GaussianDelay",
            "OpenEMS",
            "Gaussian delay in sec.",
            DEFAULTS["simulation"]["gaussian_delay"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "CustomExcitationExpression",
            "OpenEMS",
            "Custom excitation expression payload.",
            DEFAULTS["simulation"]["custom_expression"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "OutputDirectory",
            "OpenEMS",
            "Simulation output directory.",
            "",
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "SolverExecutable",
            "Run",
            "Executable used to run generated openEMS script.",
            DEFAULTS["simulation"]["solver_executable"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyString",
            "SolverArguments",
            "Run",
            "Optional arguments passed to the solver executable.",
            DEFAULTS["simulation"]["solver_arguments"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyBool",
            "RunBlocking",
            "Run",
            "Run solver synchronously in FreeCAD UI thread.",
            DEFAULTS["simulation"]["run_blocking"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyBool",
            "RunInTerminalWindow",
            "Run",
            "Launch solver in a dedicated terminal window and stream output there.",
            DEFAULTS["simulation"]["run_in_terminal_window"],
            )
            add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "MaxRunSeconds",
            "Run",
            "Maximum run duration in seconds (0 disables timeout).",
            DEFAULTS["simulation"]["max_run_seconds"],
            )
            set_enum_choices(
            obj,
            "CoordinateSystem",
            COORDINATE_SYSTEMS,
            DEFAULTS["simulation"]["coordinate_system"],
            )
            set_enum_choices(
            obj,
            "ExcitationType",
            EXCITATION_TYPES,
            DEFAULTS["simulation"]["excitation_type"],
            )
            self._enforce_delta_unit(obj)
            _refresh_time_display_fields(obj)
            self._apply_editor_modes(obj)
        finally:
            self._is_syncing_properties = False

    def onChanged(self, obj, prop: str) -> None:  # noqa: N802 - FreeCAD API
        if getattr(self, "_is_restoring", False):
            return
        if getattr(self, "_is_syncing_properties", False):
            return
        if getattr(self, "_suspend_timestep_updates", False):
            return
        if prop == "DeltaUnit":
            self._enforce_delta_unit(obj)
        if prop in {
            "MaxSimulationTime",
            "ComputedTimeStep",
        }:
            _refresh_time_display_fields(obj)
        if prop in {
            "DeltaUnit",
            "MaxSimulationTime",
            "CoordinateSystem",
        }:
            try:
                recompute_simulation_timestep_budget(obj)
            except Exception:
                pass


class OpenEMSSimulationViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_SimulationView"

    def _is_simulation_box_helper(self, obj) -> bool:
        if obj is None:
            return False
        if bool(getattr(obj, "OpenEMSSimulationBox", False)):
            return True
        name = str(getattr(obj, "Name", "") or "").strip().lower()
        label = str(getattr(obj, "Label", "") or "").strip().lower()
        return name.startswith("openemssimulationbox") or label == "openems simulation box"

    def _find_owner_analysis(self):
        obj = getattr(self, "Object", None)
        document = getattr(obj, "Document", None)
        if document is None:
            return None
        for candidate in list(getattr(document, "Objects", [])):
            if get_proxy_type(candidate) != "OpenEMS_Analysis":
                continue
            if obj in list(getattr(candidate, "Group", [])):
                return candidate
        return None

    def _find_simulation_box(self):
        analysis = self._find_owner_analysis()
        if analysis is not None:
            for member in list(getattr(analysis, "Group", [])):
                if self._is_simulation_box_helper(member):
                    return member

        obj = getattr(self, "Object", None)
        document = getattr(obj, "Document", None)
        if document is not None:
            for candidate in list(getattr(document, "Objects", [])):
                if self._is_simulation_box_helper(candidate):
                    return candidate
        return None

    def claimChildren(self):  # noqa: N802 - FreeCAD API
        box = self._find_simulation_box()
        return [box] if box is not None else []

    def onChanged(self, vobj, prop: str):  # noqa: N802 - FreeCAD API
        if str(prop) != "Visibility":
            return

        is_visible = bool(getattr(vobj, "Visibility", True))

        if is_visible:
            analysis = self._find_owner_analysis()
            if analysis is not None:
                try:
                    try:
                        from exporter.document_reader import refresh_simulation_box_for_analysis
                    except ImportError:
                        from OpenEMSWorkbench.exporter.document_reader import refresh_simulation_box_for_analysis
                    refresh_simulation_box_for_analysis(analysis)
                except Exception:
                    pass

        box = self._find_simulation_box()
        view_obj = getattr(box, "ViewObject", None) if box is not None else None
        if view_obj is not None:
            try:
                view_obj.Visibility = is_visible
            except Exception:
                pass
