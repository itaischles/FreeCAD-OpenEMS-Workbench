from __future__ import annotations

import math
import re
from typing import Any

try:
    from PySide2 import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
    QtCore = None
    QtGui = None
    QtWidgets = None


_FLOAT_PATTERN = re.compile(
    r"^\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*$"
)
_FLOAT_PARTIAL_PATTERN = re.compile(
    r"^\s*[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+)|(?:\d+)|(?:\.))?(?:[eE][+-]?\d*)?\s*$"
)


def parse_float_text(text: str, fallback: float = 0.0) -> float:
    candidate = str(text or "").strip()
    if not candidate:
        return float(fallback)
    try:
        return float(candidate)
    except Exception:
        return float(fallback)


def format_float_text(value: float) -> str:
    number = float(value)
    if not math.isfinite(number):
        return "0"
    if number == 0.0:
        return "0"

    abs_number = abs(number)
    if abs_number >= 1.0e4 or abs_number < 1.0e-3:
        raw = f"{number:.8e}"
        mantissa, exponent = raw.split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
        exp_value = int(exponent)
        return f"{mantissa}e{exp_value}"

    fixed = f"{number:.12f}".rstrip("0").rstrip(".")
    return fixed if fixed else "0"


if QtWidgets is not None and QtGui is not None:

    class ScientificDoubleSpinBox(QtWidgets.QDoubleSpinBox):
        def textFromValue(self, value: float) -> str:  # noqa: N802 - Qt API
            return format_float_text(value)

        def valueFromText(self, text: str) -> float:  # noqa: N802 - Qt API
            return parse_float_text(text, fallback=self.value())

        def validate(self, text: str, pos: int):  # noqa: N802 - Qt API
            candidate = str(text or "")
            if _FLOAT_PATTERN.match(candidate):
                return (QtGui.QValidator.Acceptable, text, pos)
            if _FLOAT_PARTIAL_PATTERN.match(candidate):
                return (QtGui.QValidator.Intermediate, text, pos)
            return (QtGui.QValidator.Invalid, text, pos)


class BaseObjectTaskPanel:
    """Lightweight task panel bound to one FeaturePython object."""

    PANEL_TITLE = "OpenEMS Object"
    FIELDS: list[dict[str, Any]] = []

    def __init__(self, obj: Any) -> None:
        if QtWidgets is None:
            raise RuntimeError("PySide2 is required to show task panels")

        self.obj = obj
        self._sync_object_properties()
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle(self.PANEL_TITLE)

        self._widgets: dict[str, Any] = {}
        self._build_ui()
        self._load_values()

    def _sync_object_properties(self) -> None:
        proxy = getattr(self.obj, "Proxy", None)
        ensure_properties = getattr(proxy, "ensure_properties", None)
        if callable(ensure_properties):
            try:
                ensure_properties(self.obj)
            except Exception:
                # Keep panels usable even if property sync fails in runtime edge cases.
                pass

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self.form)
        form_layout = QtWidgets.QFormLayout()
        layout.addLayout(form_layout)

        for field in self.FIELDS:
            widget = self._create_widget(field)
            self._widgets[field["name"]] = widget
            form_layout.addRow(field["label"], widget)

        layout.addStretch(1)

    def _create_widget(self, field: dict[str, Any]):
        field_type = field["type"]
        read_only = bool(field.get("readonly", False))
        if field_type == "string":
            widget = QtWidgets.QLineEdit()
            if read_only:
                widget.setReadOnly(True)
            return widget
        if field_type == "float":
            widget = ScientificDoubleSpinBox()
            decimals = int(field.get("decimals", 16))
            widget.setDecimals(max(0, min(decimals, 18)))
            widget.setRange(-1.0e300, 1.0e300)
            widget.setSingleStep(0.1)
            if read_only:
                widget.setReadOnly(True)
                widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            return widget
        if field_type == "int":
            widget = QtWidgets.QSpinBox()
            widget.setRange(-2_000_000_000, 2_000_000_000)
            if read_only:
                widget.setReadOnly(True)
                widget.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
            return widget
        if field_type == "bool":
            widget = QtWidgets.QCheckBox()
            if read_only:
                widget.setEnabled(False)
            return widget
        if field_type == "enum":
            widget = QtWidgets.QComboBox()
            for choice in field.get("choices", []):
                widget.addItem(choice)
            if read_only:
                widget.setEnabled(False)
            return widget
        raise ValueError(f"Unsupported field type: {field_type}")

    def _load_values(self) -> None:
        for field in self.FIELDS:
            name = field["name"]
            if not hasattr(self.obj, name):
                continue
            value = getattr(self.obj, name)
            self._set_widget_value(field, self._widgets[name], value)

    def _set_widget_value(self, field: dict[str, Any], widget: Any, value: Any) -> None:
        field_type = field["type"]
        if field_type == "string":
            widget.setText(str(value))
        elif field_type == "float":
            widget.setValue(float(value))
        elif field_type == "int":
            widget.setValue(int(value))
        elif field_type == "bool":
            widget.setChecked(bool(value))
        elif field_type == "enum":
            text = str(value)
            index = widget.findText(text)
            if index < 0:
                index = 0
            widget.setCurrentIndex(index)

    def _read_widget_value(self, field: dict[str, Any], widget: Any) -> Any:
        field_type = field["type"]
        if field_type == "string":
            return widget.text()
        if field_type == "float":
            return float(widget.value())
        if field_type == "int":
            return int(widget.value())
        if field_type == "bool":
            return bool(widget.isChecked())
        if field_type == "enum":
            return widget.currentText()
        raise ValueError(f"Unsupported field type: {field_type}")

    def _apply_values(self) -> None:
        for field in self.FIELDS:
            if bool(field.get("readonly", False)):
                continue
            name = field["name"]
            if not hasattr(self.obj, name):
                continue
            value = self._read_widget_value(field, self._widgets[name])
            setattr(self.obj, name, value)

    def accept(self) -> bool:
        try:
            import FreeCAD as App
            import FreeCADGui as Gui
        except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
            return True

        self._apply_values()
        if App.ActiveDocument is not None:
            App.ActiveDocument.recompute()

        if Gui.ActiveDocument is not None and Gui.ActiveDocument.getInEdit() is not None:
            Gui.ActiveDocument.resetEdit()
        else:
            Gui.Control.closeDialog()
        return True

    def reject(self) -> bool:
        try:
            import FreeCADGui as Gui
        except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
            return True

        if Gui.ActiveDocument is not None and Gui.ActiveDocument.getInEdit() is not None:
            Gui.ActiveDocument.resetEdit()
        else:
            Gui.Control.closeDialog()
        return True

    def getStandardButtons(self):  # noqa: N802 - Qt API
        if QtWidgets is None:
            return 0
        return int(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
