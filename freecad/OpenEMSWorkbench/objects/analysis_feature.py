from __future__ import annotations

try:
    from objects.base_feature import FeatureProxyBase, ViewProviderBase, add_property_if_missing
except ImportError:
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
    )


class OpenEMSAnalysisProxy(FeatureProxyBase):
    TYPE = "OpenEMS_Analysis"

    def ensure_properties(self, obj):
        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "IsActive",
            "Analysis",
            "Whether this analysis is active for object creation and checks.",
            False,
        )
        add_property_if_missing(
            obj,
            "App::PropertyString",
            "Description",
            "Analysis",
            "Optional user description for this analysis container.",
            "",
        )

    def onChanged(self, obj, prop):
        if prop != "Group" or getattr(self, "_is_restoring", False):
            return
        if bool(getattr(obj, "_openems_skip_group_refresh", False)):
            return

        try:
            try:
                from exporter.document_reader import refresh_simulation_box_for_analysis
            except ImportError:
                from OpenEMSWorkbench.exporter.document_reader import (
                    refresh_simulation_box_for_analysis,
                )

            refresh_simulation_box_for_analysis(
                obj,
            )
        except Exception:
            # Never block normal FreeCAD group edits if refresh fails.
            return


class OpenEMSAnalysisViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_AnalysisView"

    def _is_material_object(self, obj) -> bool:
        proxy = getattr(obj, "Proxy", None)
        return str(getattr(proxy, "TYPE", "")) == "OpenEMS_Material"

    def _assigned_geometry_name_set(self, analysis_obj) -> set[str]:
        names: set[str] = set()
        for member in list(getattr(analysis_obj, "Group", [])):
            if not self._is_material_object(member):
                continue
            for linked in list(getattr(member, "AssignedGeometry", [])):
                name = str(getattr(linked, "Name", "") or "").strip()
                if name:
                    names.add(name)
        return names

    def _is_simulation_box_helper(self, obj) -> bool:
        if obj is None:
            return False
        if bool(getattr(obj, "OpenEMSSimulationBox", False)):
            return True
        name = str(getattr(obj, "Name", "") or "").strip().lower()
        label = str(getattr(obj, "Label", "") or "").strip().lower()
        return name.startswith("openemssimulationbox") or label == "openems simulation box"

    def claimChildren(self):  # noqa: N802 - FreeCAD API
        obj = getattr(self, "Object", None)
        if obj is None:
            return []
        assigned_geometry_names = self._assigned_geometry_name_set(obj)
        children = []
        for member in list(getattr(obj, "Group", [])):
            if self._is_simulation_box_helper(member):
                continue
            if bool(getattr(member, "OpenEMSWaveguidePortPlane", False)):
                continue
            member_name = str(getattr(member, "Name", "") or "").strip()
            if member_name and member_name in assigned_geometry_names:
                continue
            children.append(member)
        return children
