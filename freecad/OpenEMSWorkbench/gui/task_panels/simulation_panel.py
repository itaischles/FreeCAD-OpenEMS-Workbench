from __future__ import annotations

try:
    from PySide2 import QtWidgets
except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
    QtWidgets = None

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
    from model import EXCITATION_TYPES
    from objects.simulation_feature import recompute_simulation_timestep_budget
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel
    from OpenEMSWorkbench.model import EXCITATION_TYPES
    from OpenEMSWorkbench.objects.simulation_feature import recompute_simulation_timestep_budget


class SimulationTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Simulation"
    FIELDS = [
        {"name": "SolverName", "label": "Solver Name", "type": "string"},
        {
            "name": "CoordinateSystem",
            "label": "Coordinate System",
            "type": "enum",
            "choices": ["Cartesian", "Cylindrical"],
        },
        {"name": "NumberOfTimeSteps", "label": "Computed NrTS", "type": "int", "readonly": True},
        {"name": "EndCriteria", "label": "End Criteria", "type": "float"},
        {
            "name": "ExcitationType",
            "label": "Excitation Type",
            "type": "enum",
            "choices": EXCITATION_TYPES,
        },
        {"name": "ExcitationFMax", "label": "f_max (Hz)", "type": "float"},
        {"name": "MaxSimulationTime", "label": "T_max (sec)", "type": "float"},
        {
            "name": "ComputedTimeStep",
            "label": "Computed dt (sec)",
            "type": "float",
            "decimals": 18,
            "readonly": True,
        },
        {"name": "SinusoidAmplitude", "label": "Sinusoid Amplitude", "type": "float"},
        {
            "name": "SinusoidFrequency",
            "label": "Sinusoid Frequency (Hz)",
            "type": "float",
        },
        {
            "name": "SinusoidPhaseDeg",
            "label": "Sinusoid Phase (deg)",
            "type": "float",
        },
        {"name": "GaussianAmplitude", "label": "Gaussian Amplitude", "type": "float"},
        {"name": "GaussianSigma", "label": "Gaussian Sigma (sec)", "type": "float"},
        {"name": "GaussianDelay", "label": "Gaussian Delay (sec)", "type": "float"},
        {
            "name": "CustomExcitationExpression",
            "label": "Custom Expression",
            "type": "string",
        },
        {"name": "ExcitationF0", "label": "Excitation F0 (Hz)", "type": "float"},
        {"name": "ExcitationFc", "label": "Excitation Fc (Hz)", "type": "float"},
        {"name": "OutputDirectory", "label": "Output Directory", "type": "string"},
        {"name": "SolverExecutable", "label": "Solver Executable", "type": "string"},
        {"name": "SolverArguments", "label": "Solver Arguments", "type": "string"},
        {"name": "RunBlocking", "label": "Run Blocking", "type": "bool"},
    ]

    _TOP_FIELDS = [
        "SolverName",
        "CoordinateSystem",
        "EndCriteria",
        "OutputDirectory",
        "SolverExecutable",
        "SolverArguments",
        "RunBlocking",
    ]
    _EXCITATION_COMMON_FIELDS = ["ExcitationType", "ExcitationFMax", "MaxSimulationTime"]
    _EXCITATION_COMPUTED_FIELDS = [
        "NumberOfTimeSteps",
        "ComputedTimeStep",
    ]
    _EXCITATION_GAUSSIAN_FIELDS = [
        "GaussianAmplitude",
        "GaussianSigma",
        "GaussianDelay",
        "ExcitationF0",
        "ExcitationFc",
    ]
    _EXCITATION_SINUSOID_FIELDS = ["SinusoidAmplitude", "SinusoidFrequency", "SinusoidPhaseDeg"]
    _EXCITATION_CUSTOM_FIELDS = ["CustomExcitationExpression"]

    def _field_by_name(self, name: str) -> dict:
        return next(field for field in self.FIELDS if field["name"] == name)

    def _add_field_row(self, form_layout, field_name: str) -> tuple:
        field = self._field_by_name(field_name)
        widget = self._create_widget(field)
        self._widgets[field_name] = widget
        label = QtWidgets.QLabel(field["label"])
        form_layout.addRow(label, widget)
        return label, widget

    def _build_ui(self) -> None:
        if QtWidgets is None:
            super()._build_ui()
            return

        self._field_rows = {}
        self._excitation_rows = {"Gaussian": [], "Sinusoid": [], "Custom": []}

        layout = QtWidgets.QVBoxLayout(self.form)

        base_group = QtWidgets.QGroupBox("Simulation Settings")
        base_layout = QtWidgets.QFormLayout(base_group)
        for field_name in self._TOP_FIELDS:
            self._field_rows[field_name] = self._add_field_row(base_layout, field_name)
        layout.addWidget(base_group)

        excite_group = QtWidgets.QGroupBox("Excitation Settings")
        excite_layout = QtWidgets.QFormLayout(excite_group)
        for field_name in self._EXCITATION_COMMON_FIELDS:
            self._field_rows[field_name] = self._add_field_row(excite_layout, field_name)
        for field_name in self._EXCITATION_COMPUTED_FIELDS:
            self._field_rows[field_name] = self._add_field_row(excite_layout, field_name)

        gaussian_header = QtWidgets.QLabel("Gaussian Parameters")
        sinusoid_header = QtWidgets.QLabel("Sinusoid Parameters")
        custom_header = QtWidgets.QLabel("Custom Parameters")
        excite_layout.addRow(gaussian_header)
        excite_layout.addRow(sinusoid_header)
        excite_layout.addRow(custom_header)
        self._gaussian_header = gaussian_header
        self._sinusoid_header = sinusoid_header
        self._custom_header = custom_header

        for field_name in self._EXCITATION_GAUSSIAN_FIELDS:
            row = self._add_field_row(excite_layout, field_name)
            self._field_rows[field_name] = row
            self._excitation_rows["Gaussian"].append(row)
        for field_name in self._EXCITATION_SINUSOID_FIELDS:
            row = self._add_field_row(excite_layout, field_name)
            self._field_rows[field_name] = row
            self._excitation_rows["Sinusoid"].append(row)
        for field_name in self._EXCITATION_CUSTOM_FIELDS:
            row = self._add_field_row(excite_layout, field_name)
            self._field_rows[field_name] = row
            self._excitation_rows["Custom"].append(row)

        layout.addWidget(excite_group)
        layout.addStretch(1)

        excitation_widget = self._widgets.get("ExcitationType")
        if excitation_widget is not None and hasattr(excitation_widget, "currentTextChanged"):
            excitation_widget.currentTextChanged.connect(self._update_excitation_visibility)

        self._connect_live_timestep_updates()

    def _set_rows_visible(self, rows: list[tuple], visible: bool) -> None:
        for label, widget in rows:
            label.setVisible(visible)
            widget.setVisible(visible)

    def _update_excitation_visibility(self, *_args) -> None:
        excitation_widget = self._widgets.get("ExcitationType")
        selected = "Gaussian"
        if excitation_widget is not None:
            selected = str(excitation_widget.currentText() or "Gaussian")

        gaussian_visible, sinusoid_visible, custom_visible = excitation_visibility_flags(selected)

        self._gaussian_header.setVisible(gaussian_visible)
        self._sinusoid_header.setVisible(sinusoid_visible)
        self._custom_header.setVisible(custom_visible)

        self._set_rows_visible(self._excitation_rows["Gaussian"], gaussian_visible)
        self._set_rows_visible(self._excitation_rows["Sinusoid"], sinusoid_visible)
        self._set_rows_visible(self._excitation_rows["Custom"], custom_visible)

    def _load_values(self) -> None:
        super()._load_values()
        if QtWidgets is not None:
            self._update_excitation_visibility()

    def _connect_live_timestep_updates(self) -> None:
        if QtWidgets is None:
            return

        max_time_widget = self._widgets.get("MaxSimulationTime")
        if max_time_widget is not None and hasattr(max_time_widget, "valueChanged"):
            max_time_widget.valueChanged.connect(self._on_live_timestep_input_changed)

        coord_widget = self._widgets.get("CoordinateSystem")
        if coord_widget is not None and hasattr(coord_widget, "currentTextChanged"):
            coord_widget.currentTextChanged.connect(self._on_live_timestep_input_changed)

    def _refresh_computed_dt_widget(self) -> None:
        dt_widget = self._widgets.get("ComputedTimeStep")
        if dt_widget is None or not hasattr(self.obj, "ComputedTimeStep"):
            return

        blocked = dt_widget.blockSignals(True)
        try:
            dt_widget.setValue(float(getattr(self.obj, "ComputedTimeStep", 0.0) or 0.0))
        finally:
            dt_widget.blockSignals(blocked)

    def _refresh_number_of_time_steps_widget(self, value: int) -> None:
        nrts_widget = self._widgets.get("NumberOfTimeSteps")
        if nrts_widget is None:
            return

        blocked = nrts_widget.blockSignals(True)
        try:
            nrts_widget.setValue(int(value))
        finally:
            nrts_widget.blockSignals(blocked)

    def _preview_timestep_budget(self) -> None:
        proxy = getattr(self.obj, "Proxy", None)
        original_values = {
            "MaxSimulationTime": getattr(self.obj, "MaxSimulationTime", 0.0),
            "CoordinateSystem": getattr(self.obj, "CoordinateSystem", "Cartesian"),
            "ComputedTimeStep": getattr(self.obj, "ComputedTimeStep", 0.0),
            "ComputedTimeStepDisplay": getattr(self.obj, "ComputedTimeStepDisplay", ""),
            "ComputedNumberOfTimeSteps": getattr(self.obj, "ComputedNumberOfTimeSteps", 0),
            "ComputedNumberOfTimeStepsRaw": getattr(self.obj, "ComputedNumberOfTimeStepsRaw", ""),
            "ComputedNumberOfTimeStepsScientific": getattr(self.obj, "ComputedNumberOfTimeStepsScientific", ""),
            "ComputedLengthUnitName": getattr(self.obj, "ComputedLengthUnitName", ""),
            "NumberOfTimeSteps": getattr(self.obj, "NumberOfTimeSteps", 0),
            "TimeStepBudgetStatus": getattr(self.obj, "TimeStepBudgetStatus", ""),
            "TimeStepBudgetLastReportKey": getattr(self.obj, "TimeStepBudgetLastReportKey", ""),
            "MaxSimulationTimeDisplay": getattr(self.obj, "MaxSimulationTimeDisplay", ""),
        }

        try:
            if proxy is not None:
                setattr(proxy, "_suspend_timestep_updates", True)

            self.obj.MaxSimulationTime = float(self._widgets["MaxSimulationTime"].value())
            self.obj.CoordinateSystem = str(self._widgets["CoordinateSystem"].currentText())
            recompute_simulation_timestep_budget(self.obj, emit_report=False)

            preview_dt = float(getattr(self.obj, "ComputedTimeStep", 0.0) or 0.0)
            preview_nrts = int(getattr(self.obj, "NumberOfTimeSteps", 0) or 0)
        except Exception:
            return
        finally:
            for name, value in original_values.items():
                if hasattr(self.obj, name):
                    try:
                        setattr(self.obj, name, value)
                    except Exception:
                        pass
            if proxy is not None:
                setattr(proxy, "_suspend_timestep_updates", False)

        dt_widget = self._widgets.get("ComputedTimeStep")
        if dt_widget is not None:
            blocked = dt_widget.blockSignals(True)
            try:
                dt_widget.setValue(preview_dt)
            finally:
                dt_widget.blockSignals(blocked)
        self._refresh_number_of_time_steps_widget(preview_nrts)

    def _on_live_timestep_input_changed(self, *_args) -> None:
        if not hasattr(self.obj, "MaxSimulationTime") or not hasattr(self.obj, "CoordinateSystem"):
            return
        self._preview_timestep_budget()

    def accept(self) -> bool:
        try:
            import FreeCAD as App
            import FreeCADGui as Gui
        except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
            return True

        proxy = getattr(self.obj, "Proxy", None)
        if proxy is not None:
            setattr(proxy, "_suspend_timestep_updates", True)
        try:
            self._apply_values()
        finally:
            if proxy is not None:
                setattr(proxy, "_suspend_timestep_updates", False)

        try:
            recompute_simulation_timestep_budget(self.obj)
        except Exception:
            pass

        if App.ActiveDocument is not None:
            App.ActiveDocument.recompute()

        if Gui.ActiveDocument is not None and Gui.ActiveDocument.getInEdit() is not None:
            Gui.ActiveDocument.resetEdit()
        else:
            Gui.Control.closeDialog()
        return True


def excitation_visibility_flags(excitation_type: str) -> tuple[bool, bool, bool]:
    text = str(excitation_type or "Gaussian").strip().lower()
    if text in {"sinusoid", "sinusoidal"}:
        return False, True, False
    if text in {"custom", "custom-expression", "custom_expression"}:
        return False, False, True
    return True, False, False
