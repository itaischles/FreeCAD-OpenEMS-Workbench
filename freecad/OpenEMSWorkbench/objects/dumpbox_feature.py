from __future__ import annotations

try:
    from model import DEFAULTS, DUMP_TYPES
    from objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )
except ImportError:
    from OpenEMSWorkbench.model import DEFAULTS, DUMP_TYPES
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )


class OpenEMSDumpBoxProxy(FeatureProxyBase):
    TYPE = "OpenEMS_DumpBox"

    def ensure_properties(self, obj):
        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "DumpType",
            "DumpBox",
            "Recorded field quantity.",
            DEFAULTS["dumpbox"]["dump_type"],
        )
        set_enum_choices(
            obj,
            "DumpType",
            DUMP_TYPES,
            DEFAULTS["dumpbox"]["dump_type"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "Enabled",
            "DumpBox",
            "Enable this dump box.",
            DEFAULTS["dumpbox"]["enabled"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyString",
            "FrequencySpec",
            "DumpBox",
            "Frequency range expression.",
            DEFAULTS["dumpbox"]["frequency_spec"],
        )


class OpenEMSDumpBoxViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_DumpBoxView"
