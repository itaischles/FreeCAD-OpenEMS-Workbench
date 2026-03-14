from __future__ import annotations

try:
    from model import DEFAULTS, PORT_TYPES
    from objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )
except ImportError:
    from OpenEMSWorkbench.model import DEFAULTS, PORT_TYPES
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )


class OpenEMSPortProxy(FeatureProxyBase):
    TYPE = "OpenEMS_Port"

    def ensure_properties(self, obj):
        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "PortType",
            "Port",
            "Port type definition.",
            DEFAULTS["port"]["port_type"],
        )
        set_enum_choices(
            obj,
            "PortType",
            PORT_TYPES,
            DEFAULTS["port"]["port_type"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyInteger",
            "PortNumber",
            "Port",
            "Port index in simulation.",
            DEFAULTS["port"]["port_number"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "Resistance",
            "Port",
            "Reference resistance in Ohms.",
            DEFAULTS["port"]["resistance"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "Excite",
            "Port",
            "Enable excitation on this port.",
            DEFAULTS["port"]["excite"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyString",
            "PropagationDirection",
            "Port",
            "Primary propagation direction (+x, -x, +y, -y, +z, -z).",
            DEFAULTS["port"]["propagation_direction"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStartX",
            "Port",
            "Port region start X coordinate.",
            DEFAULTS["port"]["start_x"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStartY",
            "Port",
            "Port region start Y coordinate.",
            DEFAULTS["port"]["start_y"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStartZ",
            "Port",
            "Port region start Z coordinate.",
            DEFAULTS["port"]["start_z"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStopX",
            "Port",
            "Port region stop X coordinate.",
            DEFAULTS["port"]["stop_x"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStopY",
            "Port",
            "Port region stop Y coordinate.",
            DEFAULTS["port"]["stop_y"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "PortStopZ",
            "Port",
            "Port region stop Z coordinate.",
            DEFAULTS["port"]["stop_z"],
        )


class OpenEMSPortViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_PortView"
