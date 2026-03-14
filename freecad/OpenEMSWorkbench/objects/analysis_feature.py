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


class OpenEMSAnalysisViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_AnalysisView"
