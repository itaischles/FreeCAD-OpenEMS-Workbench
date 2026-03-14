from __future__ import annotations

try:
    from model import COORDINATE_SYSTEMS, DEFAULTS
    from objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )
except ImportError:
    from OpenEMSWorkbench.model import COORDINATE_SYSTEMS, DEFAULTS
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )


class OpenEMSGridProxy(FeatureProxyBase):
    TYPE = "OpenEMS_Grid"

    def ensure_properties(self, obj):
        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "CoordinateSystem",
            "Grid",
            "Grid coordinate system.",
            DEFAULTS["grid"]["coordinate_system"],
        )
        set_enum_choices(
            obj,
            "CoordinateSystem",
            COORDINATE_SYSTEMS,
            DEFAULTS["grid"]["coordinate_system"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "BaseResolution",
            "Grid",
            "Base mesh resolution.",
            DEFAULTS["grid"]["base_resolution"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "MaxResolution",
            "Grid",
            "Maximum mesh resolution.",
            DEFAULTS["grid"]["max_resolution"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "GradingFactor",
            "Grid",
            "Mesh grading factor.",
            DEFAULTS["grid"]["grading_factor"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "AutoSmooth",
            "Grid",
            "Apply automatic smoothing to generated lines.",
            DEFAULTS["grid"]["auto_smooth"],
        )


class OpenEMSGridViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_GridView"
