from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class Proxy:
    def __init__(self, proxy_type):
        self.TYPE = proxy_type


class Obj:
    def __init__(self, name, proxy_type="", has_shape=False):
        self.Name = name
        self.Label = name
        self.Proxy = Proxy(proxy_type) if proxy_type else None
        if has_shape:
            self.Shape = object()


class Analysis:
    def __init__(self, group):
        self.Proxy = Proxy("OpenEMS_Analysis")
        self.Group = group


class Doc:
    def __init__(self, objects):
        self.Objects = objects


def test_filter_assignable_selection_only_keeps_analysis_geometry():
    from OpenEMSWorkbench.gui.task_panels.material_panel import _filter_assignable_selection

    geo_a = Obj("GeoA", has_shape=True)
    geo_b = Obj("GeoB", has_shape=True)
    not_geo = Obj("Mat", proxy_type="OpenEMS_Material")
    analysis = Analysis([geo_a])

    result = _filter_assignable_selection([geo_a, geo_b, not_geo], analysis)
    assert result == [geo_a]


def test_merge_unique_by_name_keeps_existing_order_and_skips_duplicates():
    from OpenEMSWorkbench.gui.task_panels.material_panel import _merge_unique_by_name

    geo_a = Obj("GeoA", has_shape=True)
    geo_b = Obj("GeoB", has_shape=True)
    geo_a_dup = Obj("GeoA", has_shape=True)

    result = _merge_unique_by_name([geo_a], [geo_a_dup, geo_b])
    assert [obj.Name for obj in result] == ["GeoA", "GeoB"]


def test_remove_by_name_removes_matching_entries():
    from OpenEMSWorkbench.gui.task_panels.material_panel import _remove_by_name

    geo_a = Obj("GeoA", has_shape=True)
    geo_b = Obj("GeoB", has_shape=True)
    result = _remove_by_name([geo_a, geo_b], [Obj("GeoB", has_shape=True)])
    assert [obj.Name for obj in result] == ["GeoA"]


def test_find_analysis_for_member_returns_matching_analysis():
    from OpenEMSWorkbench.gui.task_panels.material_panel import _find_analysis_for_member

    material = Obj("Material", proxy_type="OpenEMS_Material")
    other = Obj("Other", has_shape=True)
    analysis = Analysis([material, other])
    doc = Doc([analysis])

    found = _find_analysis_for_member(doc, material)
    assert found is analysis


def test_assign_reassign_unassign_flow_helpers():
    from OpenEMSWorkbench.gui.task_panels.material_panel import (
        _filter_assignable_selection,
        _merge_unique_by_name,
        _remove_by_name,
    )

    geo_a = Obj("GeoA", has_shape=True)
    geo_b = Obj("GeoB", has_shape=True)
    geo_c = Obj("GeoC", has_shape=True)
    analysis = Analysis([geo_a, geo_b, geo_c])

    # Assign: material A gets GeoA and GeoB from user selection.
    material_a_assigned = []
    selection = [geo_a, geo_b]
    material_a_assigned = _merge_unique_by_name(
        material_a_assigned,
        _filter_assignable_selection(selection, analysis),
    )
    assert [obj.Name for obj in material_a_assigned] == ["GeoA", "GeoB"]

    # Reassign: user assigns GeoB to material B, then removes it from material A.
    material_b_assigned = []
    material_b_assigned = _merge_unique_by_name(
        material_b_assigned,
        _filter_assignable_selection([geo_b], analysis),
    )
    material_a_assigned = _remove_by_name(material_a_assigned, [geo_b])
    assert [obj.Name for obj in material_a_assigned] == ["GeoA"]
    assert [obj.Name for obj in material_b_assigned] == ["GeoB"]

    # Unassign: remove the remaining geometry from material A.
    material_a_assigned = _remove_by_name(material_a_assigned, [geo_a])
    assert material_a_assigned == []
