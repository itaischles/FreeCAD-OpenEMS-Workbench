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

    def claimChildren(self):  # noqa: N802 - FreeCAD API
        obj = getattr(self, "Object", None)
        if obj is None:
            return []
        return list(getattr(obj, "Group", []))
