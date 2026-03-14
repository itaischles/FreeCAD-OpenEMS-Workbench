from __future__ import annotations

from typing import Any

try:
    from PySide2 import QtCore, QtWidgets
except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
    QtCore = None
    QtWidgets = None


class BaseObjectTaskPanel:
    """Lightweight task panel bound to one FeaturePython object."""

    PANEL_TITLE = "OpenEMS Object"
    FIELDS: list[dict[str, Any]] = []

    def __init__(self, obj: Any) -> None:
        if QtWidgets is None:
            raise RuntimeError("PySide2 is required to show task panels")

        self.obj = obj
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle(self.PANEL_TITLE)

        self._widgets: dict[str, Any] = {}
        self._build_ui()
        self._load_values()

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
        if field_type == "string":
            return QtWidgets.QLineEdit()
        if field_type == "float":
            widget = QtWidgets.QDoubleSpinBox()
            widget.setDecimals(8)
            widget.setRange(-1.0e15, 1.0e15)
            widget.setSingleStep(0.1)
            return widget
        if field_type == "int":
            widget = QtWidgets.QSpinBox()
            widget.setRange(-2_000_000_000, 2_000_000_000)
            return widget
        if field_type == "bool":
            return QtWidgets.QCheckBox()
        if field_type == "enum":
            widget = QtWidgets.QComboBox()
            for choice in field.get("choices", []):
                widget.addItem(choice)
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
