from __future__ import annotations

from typing import Any

try:
    import FreeCAD as App
except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
    App = None

try:
    from PySide2 import QtWidgets
except ImportError:  # pragma: no cover - runtime only in FreeCAD GUI
    QtWidgets = None

try:
    from exporter.document_reader import refresh_simulation_box_for_analysis
    from exporter.port_geometry import detect_waveguide_face_geometry
    from exporter.port_inference import infer_coax_from_waveguide_detection
    from gui.task_panels.base_panel import BaseObjectTaskPanel
    from utils.analysis_context import get_proxy_type
except ImportError:
    from OpenEMSWorkbench.exporter.document_reader import refresh_simulation_box_for_analysis
    from OpenEMSWorkbench.exporter.port_geometry import detect_waveguide_face_geometry
    from OpenEMSWorkbench.exporter.port_inference import infer_coax_from_waveguide_detection
    from OpenEMSWorkbench.gui.task_panels.base_panel import BaseObjectTaskPanel
    from OpenEMSWorkbench.utils.analysis_context import get_proxy_type


def _find_analysis_for_member(doc: Any, member: Any) -> Any | None:
    if doc is None or member is None:
        return None
    for obj in list(getattr(doc, "Objects", [])):
        if get_proxy_type(obj) != "OpenEMS_Analysis":
            continue
        if member in list(getattr(obj, "Group", [])):
            return obj
    return None


def _collect_geometry_objects(analysis: Any) -> list[Any]:
    geometry = []
    for obj in list(getattr(analysis, "Group", [])):
        if bool(getattr(obj, "OpenEMSSimulationBox", False)):
            continue
        proxy_type = get_proxy_type(obj)
        if proxy_type.startswith("OpenEMS_"):
            continue
        if hasattr(obj, "Shape"):
            geometry.append(obj)
    geometry.sort(key=lambda item: str(getattr(item, "Name", "")))
    return geometry


def _collect_material_entries(analysis: Any) -> list[dict[str, Any]]:
    entries = []
    for obj in list(getattr(analysis, "Group", [])):
        if get_proxy_type(obj) != "OpenEMS_Material":
            continue
        name = str(getattr(obj, "Name", "") or "")
        assigned = []
        for item in list(getattr(obj, "AssignedGeometry", []) or []):
            geometry_name = str(getattr(item, "Name", "") or "").strip()
            if geometry_name:
                assigned.append(geometry_name)
        entries.append(
            {
                "name": name,
                "IsPEC": bool(getattr(obj, "IsPEC", False)),
                "EpsilonR": float(getattr(obj, "EpsilonR", 0.0) or 0.0),
                "AssignedGeometryNames": sorted(set(assigned)),
            }
        )
    return entries


def _material_maps(material_entries: list[dict[str, Any]]) -> tuple[dict[str, list[str]], dict[str, dict[str, Any]]]:
    geometry_to_materials: dict[str, set[str]] = {}
    materials_by_name: dict[str, dict[str, Any]] = {}
    for material in material_entries:
        name = str(material.get("name", "") or "").strip()
        if not name:
            continue
        materials_by_name[name] = material
        for geometry_name in material.get("AssignedGeometryNames", []):
            key = str(geometry_name or "").strip()
            if not key:
                continue
            geometry_to_materials.setdefault(key, set()).add(name)
    return ({key: sorted(value) for key, value in geometry_to_materials.items()}, materials_by_name)


def _waveguide_summary_text(detection: dict[str, Any] | None, inference: dict[str, Any] | None) -> str:
    if not detection:
        return "No waveguide detection yet."

    if str(detection.get("status", "")) != "supported":
        reason = str(detection.get("reason", "unknown"))
        lines = [f"Geometry detection: unsupported ({reason})."]
        if detection.get("selected_face"):
            lines.append(
                f"Selected face: {detection.get('selected_face')} | Axis: {detection.get('axis', '?')}"
            )
        candidates = list(detection.get("candidates", []) or [])
        if candidates:
            lines.append("Cylinder-like candidates seen on selected face:")
            for item in candidates:
                lines.append(
                    f"- {item.get('geometry_name')} r={item.get('radius')} source={item.get('radius_source', 'bounds')} materials={item.get('material_names', [])}"
                )
        else:
            lines.append("Cylinder-like candidates seen on selected face: none")

        inspected = list(detection.get("inspected", []) or [])
        if inspected:
            lines.append("Inspected solids:")
            for item in inspected:
                bounds = item.get("bounds", {}) or {}
                lines.append(
                    "- "
                    f"{item.get('geometry_name')} "
                    f"touches_face={item.get('touched_selected_face')} "
                    f"axis={item.get('inferred_axis')} "
                    f"radius={item.get('inferred_radius')} "
                    f"support={item.get('support_reason')} "
                    f"reject={item.get('rejection_reason')} "
                    f"radius_props={item.get('radius_from_properties')} "
                    f"bounds={bounds}"
                )
        return "\n".join(lines)

    lines = [
        f"Geometry detection: supported ({detection.get('kind')}).",
        f"Selected face: {detection.get('selected_face')} | Axis: {detection.get('axis')}",
        f"Inner conductor: {detection.get('inner', {}).get('geometry_name')} r={detection.get('inner', {}).get('radius')}",
        f"Outer conductor: {detection.get('outer', {}).get('geometry_name')} r={detection.get('outer', {}).get('radius')}",
    ]

    if inference:
        if str(inference.get("status", "")) == "supported":
            z0 = inference.get("z0_ohm")
            lines.append(
                "Inferred coax: "
                f"r_in={inference.get('r_in')}, "
                f"r_out={inference.get('r_out')}, "
                f"epsilon_r={inference.get('dielectric_epsilon_r')}, "
                f"Z0={z0} Ohm"
            )
        else:
            lines.append(f"Coax inference: unsupported ({inference.get('reason', 'unknown')}).")

    return "\n".join(lines)


def _inferred_coax_report_line(inference: dict[str, Any] | None) -> str | None:
    if not inference or str(inference.get("status", "")) != "supported":
        return None
    return (
        "Inferred coax: "
        f"r_in={inference.get('r_in')}, "
        f"r_out={inference.get('r_out')}, "
        f"epsilon_r={inference.get('dielectric_epsilon_r')}, "
        f"Z0={inference.get('z0_ohm')} Ohm"
    )


def _waveguide_report_line(detection: dict[str, Any] | None, inference: dict[str, Any] | None) -> str | None:
    success_line = _inferred_coax_report_line(inference)
    if success_line is not None:
        return success_line

    if not detection:
        return None
    if str(detection.get("status", "")) == "supported":
        return None

    selected_face = str(detection.get("selected_face", "") or "?")
    reason = str(detection.get("reason", "unknown") or "unknown")
    return f"No supported coax geometry detected on {selected_face} ({reason})."


class PortTaskPanel(BaseObjectTaskPanel):
    PANEL_TITLE = "OpenEMS Port"
    FIELDS = [
        {
            "name": "PortType",
            "label": "Port Type",
            "type": "enum",
            "choices": ["Lumped", "Waveguide", "PlaneWave"],
        },
        {"name": "PortNumber", "label": "Port Number", "type": "int"},
        {"name": "Resistance", "label": "Resistance (Ohm)", "type": "float"},
        {"name": "Excite", "label": "Excite", "type": "bool"},
        {
            "name": "SimulationBoxFace",
            "label": "Waveguide Face",
            "type": "enum",
            "choices": ["XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"],
        },
        {
            "name": "SourcePlaneOffsetCells",
            "label": "Source Plane Offset (Cells)",
            "type": "int",
        },
        {
            "name": "PropagationDirection",
            "label": "Propagation Direction",
            "type": "enum",
            "choices": ["+x", "-x", "+y", "-y", "+z", "-z"],
        },
        {"name": "PortStartX", "label": "Port Start X", "type": "float"},
        {"name": "PortStartY", "label": "Port Start Y", "type": "float"},
        {"name": "PortStartZ", "label": "Port Start Z", "type": "float"},
        {"name": "PortStopX", "label": "Port Stop X", "type": "float"},
        {"name": "PortStopY", "label": "Port Stop Y", "type": "float"},
        {"name": "PortStopZ", "label": "Port Stop Z", "type": "float"},
    ]

    def _build_ui(self) -> None:
        super()._build_ui()

        if QtWidgets is None:
            return

        offset_widget = self._widgets.get("SourcePlaneOffsetCells")
        if offset_widget is not None:
            offset_widget.setRange(2, 9)

        self._preview_status_label = QtWidgets.QLabel("")
        self._preview_status_label.setWordWrap(True)
        self.form.layout().insertWidget(1, self._preview_status_label)

        for key in ("PortType", "SimulationBoxFace", "SourcePlaneOffsetCells", "PropagationDirection"):
            widget = self._widgets.get(key)
            if widget is None:
                continue
            if hasattr(widget, "currentTextChanged"):
                widget.currentTextChanged.connect(self._on_waveguide_controls_changed)
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._on_waveguide_controls_changed)

        self._refresh_waveguide_preview()
        self._refresh_waveguide_summary()

    def _on_waveguide_controls_changed(self, *_args) -> None:
        # Apply key waveguide controls immediately so preview updates while editing.
        port_type_widget = self._widgets.get("PortType")
        face_widget = self._widgets.get("SimulationBoxFace")
        offset_widget = self._widgets.get("SourcePlaneOffsetCells")
        direction_widget = self._widgets.get("PropagationDirection")

        if port_type_widget is not None:
            self.obj.PortType = str(port_type_widget.currentText() or "")
        if face_widget is not None:
            self.obj.SimulationBoxFace = str(face_widget.currentText() or "")
        if offset_widget is not None:
            self.obj.SourcePlaneOffsetCells = int(offset_widget.value())
        if direction_widget is not None:
            self.obj.PropagationDirection = str(direction_widget.currentText() or "")

        if App is not None and App.ActiveDocument is not None:
            try:
                App.ActiveDocument.recompute()
            except Exception:
                pass

        self._refresh_waveguide_preview()
        self._refresh_waveguide_summary()

    def _refresh_waveguide_preview(self) -> None:
        proxy = getattr(self.obj, "Proxy", None)
        refresh_preview = getattr(proxy, "_refresh_waveguide_preview", None)
        if callable(refresh_preview):
            try:
                shown, message = refresh_preview(self.obj)
                if hasattr(self, "_preview_status_label"):
                    prefix = "Preview visible" if shown else "Preview hidden"
                    self._preview_status_label.setText(f"{prefix}: {message}")
            except Exception:
                if hasattr(self, "_preview_status_label"):
                    self._preview_status_label.setText("Preview hidden: preview refresh raised an exception.")

    def _selected_port_type(self) -> str:
        widget = self._widgets.get("PortType")
        if widget is None:
            return str(getattr(self.obj, "PortType", "") or "")
        return str(widget.currentText() or "")

    def _selected_simulation_face(self) -> str:
        widget = self._widgets.get("SimulationBoxFace")
        if widget is None:
            return str(getattr(self.obj, "SimulationBoxFace", "") or "")
        return str(widget.currentText() or "")

    def _apply_inferred_impedance(self, inference: dict[str, Any] | None) -> None:
        if not inference or str(inference.get("status", "")) != "supported":
            return

        try:
            z0 = float(inference.get("z0_ohm"))
        except Exception:
            return
        if z0 <= 0.0:
            return

        self.obj.Resistance = z0
        resistance_widget = self._widgets.get("Resistance")
        if resistance_widget is not None and hasattr(resistance_widget, "setValue"):
            try:
                resistance_widget.setValue(z0)
            except Exception:
                pass

    def _refresh_waveguide_summary(self) -> None:
        if QtWidgets is None:
            return

        if self._selected_port_type() != "Waveguide":
            return

        document = getattr(self.obj, "Document", None)
        analysis = _find_analysis_for_member(document, self.obj)
        if analysis is None:
            return

        try:
            simulation_box = refresh_simulation_box_for_analysis(analysis)
        except Exception:
            return

        geometry_objects = _collect_geometry_objects(analysis)
        material_entries = _collect_material_entries(analysis)
        geometry_to_materials, materials_by_name = _material_maps(material_entries)

        detection = detect_waveguide_face_geometry(
            geometry_objects=geometry_objects,
            simulation_box=simulation_box,
            selected_face=self._selected_simulation_face(),
            material_names_by_geometry=geometry_to_materials,
        )
        inference = infer_coax_from_waveguide_detection(
            detection=detection,
            materials_by_name=materials_by_name,
        )
        self._apply_inferred_impedance(inference)
        report_line = _waveguide_report_line(detection, inference)
        if App is not None and hasattr(App, "Console"):
            if report_line is not None:
                try:
                    App.Console.PrintMessage(f"{report_line}\n")
                except Exception:
                    pass
