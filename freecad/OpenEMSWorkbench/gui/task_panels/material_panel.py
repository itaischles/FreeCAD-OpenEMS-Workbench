from __future__ import annotations

from typing import Any

try:
    from PySide2 import QtCore, QtWidgets
except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
    QtCore = None
    QtWidgets = None

try:
    from gui.task_panels.base_panel import BaseObjectTaskPanel
    from utils.analysis_context import get_proxy_type
except ImportError:
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel
    from OpenEMSWorkbench.utils.analysis_context import get_proxy_type


def _is_geometry_object(obj: Any) -> bool:
    if obj is None:
        return False
    proxy_type = get_proxy_type(obj)
    if proxy_type.startswith("OpenEMS_"):
        return False
    return hasattr(obj, "Shape")


def _find_analysis_for_member(doc: Any, member: Any) -> Any | None:
    if doc is None or member is None:
        return None

    for obj in list(getattr(doc, "Objects", [])):
        if get_proxy_type(obj) != "OpenEMS_Analysis":
            continue
        if member in list(getattr(obj, "Group", [])):
            return obj
    return None


def _names(values: list[Any]) -> set[str]:
    result = set()
    for obj in values:
        name = str(getattr(obj, "Name", "")).strip()
        if name:
            result.add(name)
    return result


def _merge_unique_by_name(existing: list[Any], incoming: list[Any]) -> list[Any]:
    result = list(existing)
    known = _names(result)
    for obj in incoming:
        name = str(getattr(obj, "Name", "")).strip()
        if not name or name in known:
            continue
        result.append(obj)
        known.add(name)
    return result


def _filter_assignable_selection(selection: list[Any], analysis: Any | None) -> list[Any]:
    filtered = []
    analysis_group = list(getattr(analysis, "Group", [])) if analysis is not None else []
    for obj in selection:
        if not _is_geometry_object(obj):
            continue
        if analysis is not None and obj not in analysis_group:
            continue
        filtered.append(obj)
    return filtered


def _remove_by_name(existing: list[Any], to_remove: list[Any]) -> list[Any]:
    remove_names = _names(to_remove)
    if not remove_names:
        return list(existing)
    result = []
    for obj in existing:
        if str(getattr(obj, "Name", "")).strip() in remove_names:
            continue
        result.append(obj)
    return result


def _display_label(obj: Any) -> str:
    name = str(getattr(obj, "Name", "")).strip()
    label = str(getattr(obj, "Label", "")).strip()
    if label and name and label != name:
        return f"{label} ({name})"
    return label or name or "<unnamed>"


class MaterialTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Material"
    FIELDS = [
        {"name": "EpsilonR", "label": "Epsilon R", "type": "float"},
        {"name": "MuR", "label": "Mu R", "type": "float"},
        {"name": "Kappa", "label": "Kappa (S/m)", "type": "float"},
        {"name": "IsPEC", "label": "Is PEC", "type": "bool"},
        {"name": "AssignmentPriority", "label": "Assignment Priority", "type": "int"},
    ]

    def _build_ui(self) -> None:
        super()._build_ui()

        if QtWidgets is None:
            return

        self._analysis = self._get_material_analysis()

        group = QtWidgets.QGroupBox("Assigned Geometry")
        group_layout = QtWidgets.QVBoxLayout(group)

        self._assigned_list = QtWidgets.QListWidget()
        self._assigned_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        group_layout.addWidget(self._assigned_list)

        button_row = QtWidgets.QHBoxLayout()
        self._assign_button = QtWidgets.QPushButton("Assign Selected")
        self._unassign_button = QtWidgets.QPushButton("Unassign Selected")
        button_row.addWidget(self._assign_button)
        button_row.addWidget(self._unassign_button)
        group_layout.addLayout(button_row)

        self._assign_button.clicked.connect(self._assign_current_selection)
        self._unassign_button.clicked.connect(self._unassign_selected_geometry)

        priority_widget = self._widgets.get("AssignmentPriority")
        if priority_widget is not None:
            priority_widget.setRange(0, 2_000_000_000)

        self.form.layout().insertWidget(1, group)
        self._refresh_assigned_list()

    def _get_material_analysis(self):
        try:
            import FreeCAD as App
        except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
            return None

        return _find_analysis_for_member(App.ActiveDocument, self.obj)

    def _get_gui_selection(self) -> list[Any]:
        try:
            import FreeCADGui as Gui
        except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
            return []

        return list(Gui.Selection.getSelection())

    def _assigned_geometry(self) -> list[Any]:
        value = getattr(self.obj, "AssignedGeometry", [])
        if isinstance(value, (list, tuple)):
            return list(value)
        return []

    def _set_assigned_geometry(self, values: list[Any]) -> None:
        setattr(self.obj, "AssignedGeometry", list(values))

    def _refresh_assigned_list(self) -> None:
        if QtWidgets is None or not hasattr(self, "_assigned_list"):
            return

        self._assigned_list.clear()
        for obj in self._assigned_geometry():
            item = QtWidgets.QListWidgetItem(_display_label(obj))
            item.setData(QtCore.Qt.UserRole, str(getattr(obj, "Name", "")))
            self._assigned_list.addItem(item)

    def _assign_current_selection(self) -> None:
        selected = self._get_gui_selection()
        assignable = _filter_assignable_selection(selected, getattr(self, "_analysis", None))
        current = self._assigned_geometry()
        self._set_assigned_geometry(_merge_unique_by_name(current, assignable))
        self._refresh_assigned_list()

    def _unassign_selected_geometry(self) -> None:
        current = self._assigned_geometry()
        if QtWidgets is None:
            self._set_assigned_geometry(current)
            return

        selected_names = set()
        if hasattr(self, "_assigned_list"):
            for item in self._assigned_list.selectedItems():
                selected_names.add(str(item.data(QtCore.Qt.UserRole) or ""))

        if selected_names:
            remaining = [
                obj
                for obj in current
                if str(getattr(obj, "Name", "")).strip() not in selected_names
            ]
        else:
            selected = self._get_gui_selection()
            remaining = _remove_by_name(current, selected)

        self._set_assigned_geometry(remaining)
        self._refresh_assigned_list()
