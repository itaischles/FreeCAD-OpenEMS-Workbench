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
            "Recorded field quantity (MVP: EField only).",
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
            "App::PropertyEnumeration",
            "DumpMode",
            "DumpBox",
            "Dump output mode (MVP: TimeDomain only).",
            DEFAULTS["dumpbox"]["dump_mode"],
        )
        set_enum_choices(
            obj,
            "DumpMode",
            ["TimeDomain"],
            DEFAULTS["dumpbox"]["dump_mode"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "PlaneAxis",
            "DumpBox",
            "Axis normal to the dump plane.",
            DEFAULTS["dumpbox"]["plane_axis"],
        )
        set_enum_choices(
            obj,
            "PlaneAxis",
            ["X", "Y", "Z"],
            DEFAULTS["dumpbox"]["plane_axis"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "Enabled",
            "DumpBox",
            "Enable this dump box.",
            DEFAULTS["dumpbox"]["enabled"],
        )


class OpenEMSDumpBoxViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_DumpBoxView"
