from __future__ import annotations

try:
    from model import DEFAULTS
    from objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
    )
except ImportError:
    from OpenEMSWorkbench.model import DEFAULTS
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
    )


class OpenEMSMaterialProxy(FeatureProxyBase):
    TYPE = "OpenEMS_Material"

    def ensure_properties(self, obj):
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "EpsilonR",
            "Material",
            "Relative permittivity.",
            DEFAULTS["material"]["epsilon_r"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "MuR",
            "Material",
            "Relative permeability.",
            DEFAULTS["material"]["mu_r"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "Kappa",
            "Material",
            "Conductivity in S/m.",
            DEFAULTS["material"]["kappa"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "IsPEC",
            "Material",
            "Use perfect electric conductor model.",
            DEFAULTS["material"]["is_pec"],
        )


class OpenEMSMaterialViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_MaterialView"
