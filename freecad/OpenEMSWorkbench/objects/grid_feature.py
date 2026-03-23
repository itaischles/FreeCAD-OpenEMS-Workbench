from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD runtime only
    App = None

try:
    from model import COORDINATE_SYSTEMS, DEFAULTS
    from meshing import build_mesh_for_analysis
    from visualization import hide_overlay, show_overlay
    from utils.analysis_context import get_proxy_type
    from objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )
except ImportError:
    from OpenEMSWorkbench.model import COORDINATE_SYSTEMS, DEFAULTS
    from OpenEMSWorkbench.meshing import build_mesh_for_analysis
    from OpenEMSWorkbench.visualization import hide_overlay, show_overlay
    from OpenEMSWorkbench.utils.analysis_context import get_proxy_type
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )


class OpenEMSGridProxy(FeatureProxyBase):
    TYPE = "OpenEMS_Grid"

    _OVERLAY_RELEVANT_PROPERTIES = {
        "CoordinateSystem",
        "MeshBaseStep",
        "MeshMaxStep",
        "MeshGrowthRate",
        "MeshAutoSmooth",
        "MeshPreviewLineCap",
    }

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

    def onChanged(self, obj, prop: str) -> None:  # noqa: N802 - FreeCAD API
        if str(prop) not in self._OVERLAY_RELEVANT_PROPERTIES:
            return

        view_obj = getattr(obj, "ViewObject", None)
        if view_obj is None or not bool(getattr(view_obj, "Visibility", True)):
            return

        view_proxy = getattr(view_obj, "Proxy", None)
        refresh = getattr(view_proxy, "refresh_overlay_from_grid_change", None)
        if callable(refresh):
            refresh()


class OpenEMSGridViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_GridView"

    def _find_owner_analysis(self):
        obj = getattr(self, "Object", None)
        document = getattr(obj, "Document", None)
        if document is None:
            return None
        for candidate in list(getattr(document, "Objects", [])):
            if get_proxy_type(candidate) != "OpenEMS_Analysis":
                continue
            if obj in list(getattr(candidate, "Group", [])):
                return candidate
        return None

    def _show_grid_overlay(self) -> None:
        analysis = self._find_owner_analysis()
        if analysis is None:
            return
        try:
            _, _, mesh = build_mesh_for_analysis(analysis)
        except Exception:
            return
        show_overlay(mesh)

    def refresh_overlay_from_grid_change(self) -> None:
        obj = getattr(self, "Object", None)
        view_obj = getattr(obj, "ViewObject", None)
        if view_obj is None or not bool(getattr(view_obj, "Visibility", True)):
            return
        self._show_grid_overlay()

    def onChanged(self, vobj, prop: str):  # noqa: N802 - FreeCAD API
        if str(prop) != "Visibility":
            return

        is_visible = bool(getattr(vobj, "Visibility", True))
        if not is_visible:
            hide_overlay()
            return

        self._show_grid_overlay()
        if App is not None:
            try:
                App.Console.PrintMessage("OpenEMS: Mesh overlay shown from Grid visibility.\n")
            except Exception:
                pass
