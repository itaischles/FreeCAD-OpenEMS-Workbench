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
        add_property_if_missing(
            obj,
            "App::PropertyLinkList",
            "AssignedGeometry",
            "Assignment",
            "Geometry objects assigned to this material.",
            [],
        )
        add_property_if_missing(
            obj,
            "App::PropertyInteger",
            "AssignmentPriority",
            "Assignment",
            "Primitive priority for overlap resolution during export.",
            DEFAULTS["material"]["assignment_priority"],
        )


class OpenEMSMaterialViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_MaterialView"

    def claimChildren(self):  # noqa: N802 - FreeCAD API
        obj = getattr(self, "Object", None)
        if obj is None:
            return []
        return list(getattr(obj, "AssignedGeometry", []))

    def onChanged(self, vobj, prop: str):  # noqa: N802 - FreeCAD API
        if str(prop) != "Visibility":
            return

        obj = getattr(self, "Object", None)
        if obj is None:
            return

        is_visible = bool(getattr(vobj, "Visibility", True))
        for child in list(getattr(obj, "AssignedGeometry", [])):
            view_obj = getattr(child, "ViewObject", None)
            if view_obj is None:
                continue
            try:
                view_obj.Visibility = is_visible
            except Exception:
                continue
