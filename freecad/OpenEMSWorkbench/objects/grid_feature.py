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
            "Grid coordinate system used for mesh generation.",
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
            "MeshBaseStep",
            "Grid",
            "Base mesh step size in model units.",
            DEFAULTS["grid"]["mesh_base_step"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "MeshMaxStep",
            "Grid",
            "Maximum mesh step size in model units.",
            DEFAULTS["grid"]["mesh_max_step"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "MeshGrowthRate",
            "Grid",
            "Mesh growth rate between neighboring steps.",
            DEFAULTS["grid"]["mesh_growth_rate"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "MeshAutoSmooth",
            "Grid",
            "Apply automatic smoothing to generated lines.",
            DEFAULTS["grid"]["mesh_auto_smooth"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyInteger",
            "MeshPreviewLineCap",
            "Grid",
            "Maximum mesh lines per axis for 3D preview rendering.",
            DEFAULTS["grid"]["mesh_preview_line_cap"],
        )


class OpenEMSGridViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_GridView"
