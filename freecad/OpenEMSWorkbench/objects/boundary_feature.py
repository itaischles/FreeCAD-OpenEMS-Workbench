from __future__ import annotations

try:
    from model import BOUNDARY_TYPES, DEFAULTS
    from objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )
except ImportError:
    from OpenEMSWorkbench.model import BOUNDARY_TYPES, DEFAULTS
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )


class OpenEMSBoundaryProxy(FeatureProxyBase):
    TYPE = "OpenEMS_Boundary"

    def ensure_properties(self, obj):
        for key in ["XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax"]:
            add_property_if_missing(
                obj,
                "App::PropertyEnumeration",
                key,
                "Boundary",
                f"Boundary condition for {key}.",
                DEFAULTS["boundary"][key.lower()],
            )
            set_enum_choices(
                obj,
                key,
                BOUNDARY_TYPES,
                DEFAULTS["boundary"][key.lower()],
            )

        add_property_if_missing(
            obj,
            "App::PropertyInteger",
            "PMLCells",
            "Boundary",
            "Number of PML cells when using PML boundaries.",
            DEFAULTS["boundary"]["pml_cells"],
        )


class OpenEMSBoundaryViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_BoundaryView"
