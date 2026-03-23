from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class FakeObject:
    def __init__(self):
        self._props = {}

    def addProperty(self, prop_type, prop_name, group, description):
        self._props[prop_name] = {
            "type": prop_type,
            "group": group,
            "description": description,
        }


def test_grid_proxy_adds_mesh_preview_line_cap_property():
    from OpenEMSWorkbench.objects.grid_feature import OpenEMSGridProxy

    obj = FakeObject()
    proxy = OpenEMSGridProxy()
    proxy.ensure_properties(obj)

    assert obj.MeshPreviewLineCap == 96
    assert obj._props["MeshPreviewLineCap"]["type"] == "App::PropertyInteger"
    assert obj._props["MeshPreviewLineCap"]["group"] == "Grid"


def test_grid_proxy_ensure_properties_is_idempotent_for_preview_cap():
    from OpenEMSWorkbench.objects.grid_feature import OpenEMSGridProxy

    obj = FakeObject()
    proxy = OpenEMSGridProxy()
    proxy.ensure_properties(obj)
    obj.MeshPreviewLineCap = 24

    proxy.ensure_properties(obj)

    assert obj.MeshPreviewLineCap == 24
    assert list(obj._props).count("MeshPreviewLineCap") == 1


def test_grid_viewprovider_visibility_toggles_overlay(monkeypatch):
    from OpenEMSWorkbench.objects import grid_feature
    from OpenEMSWorkbench.objects.grid_feature import OpenEMSGridViewProvider

    class _AnalysisProxy:
        TYPE = "OpenEMS_Analysis"

    calls = {"show": 0, "hide": 0}

    simulation_mesh = object()
    monkeypatch.setattr(
        grid_feature,
        "build_mesh_for_analysis",
        lambda analysis: (analysis, None, simulation_mesh),
    )
    monkeypatch.setattr(grid_feature, "show_overlay", lambda mesh: calls.__setitem__("show", calls["show"] + 1) or (True, "ok"))
    monkeypatch.setattr(grid_feature, "hide_overlay", lambda: calls.__setitem__("hide", calls["hide"] + 1) or (True, "ok"))

    grid_obj = type("Grid", (), {})()
    analysis_obj = type("Analysis", (), {"Proxy": _AnalysisProxy(), "Group": [grid_obj]})()
    doc = type("Doc", (), {"Objects": [analysis_obj]})()
    grid_obj.Document = doc

    viewprovider = OpenEMSGridViewProvider()
    vobj = type("ViewObj", (), {"Object": grid_obj, "Visibility": True})()
    viewprovider.attach(vobj)

    viewprovider.onChanged(vobj, "Visibility")
    assert calls["show"] == 1

    vobj.Visibility = False
    viewprovider.onChanged(vobj, "Visibility")
    assert calls["hide"] == 1
