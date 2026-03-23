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


def test_material_proxy_adds_assignment_properties_with_defaults():
    from OpenEMSWorkbench.objects.material_feature import OpenEMSMaterialProxy

    obj = FakeObject()
    proxy = OpenEMSMaterialProxy()
    proxy.ensure_properties(obj)

    assert obj.EpsilonR == 1.0
    assert obj.MuR == 1.0
    assert obj.Kappa == 0.0
    assert obj.IsPEC is False
    assert obj.AssignedGeometry == []
    assert obj.AssignmentPriority == 0

    assert obj._props["AssignedGeometry"]["type"] == "App::PropertyLinkList"
    assert obj._props["AssignedGeometry"]["group"] == "Assignment"
    assert obj._props["AssignmentPriority"]["type"] == "App::PropertyInteger"
    assert obj._props["AssignmentPriority"]["group"] == "Assignment"


def test_material_proxy_ensure_properties_is_idempotent():
    from OpenEMSWorkbench.objects.material_feature import OpenEMSMaterialProxy

    obj = FakeObject()
    proxy = OpenEMSMaterialProxy()

    proxy.ensure_properties(obj)
    obj.AssignmentPriority = 7
    proxy.ensure_properties(obj)

    assert obj.AssignmentPriority == 7
    assert list(obj._props).count("AssignedGeometry") == 1
    assert list(obj._props).count("AssignmentPriority") == 1


class _GeoObj:
    def __init__(self, name):
        self.Name = name
        self.Label = name
        self.Shape = object()


def test_material_proxy_restore_keeps_assignment_values():
    from OpenEMSWorkbench.objects.material_feature import OpenEMSMaterialProxy

    geo_a = _GeoObj("GeoA")
    geo_b = _GeoObj("GeoB")

    obj = FakeObject()
    proxy = OpenEMSMaterialProxy()
    proxy.ensure_properties(obj)

    obj.AssignedGeometry = [geo_a, geo_b]
    obj.AssignmentPriority = 11

    # Simulate FreeCAD document reopen lifecycle callback.
    proxy.onDocumentRestored(obj)

    assert [item.Name for item in obj.AssignedGeometry] == ["GeoA", "GeoB"]
    assert obj.AssignmentPriority == 11


def test_material_viewprovider_claims_assigned_geometry_children_for_tree_nesting():
    from OpenEMSWorkbench.objects.material_feature import OpenEMSMaterialViewProvider

    geo_a = _GeoObj("GeoA")
    geo_b = _GeoObj("GeoB")

    class _ViewObjectStub:
        def __init__(self):
            self.Object = type("Material", (), {"AssignedGeometry": [geo_a, geo_b]})()

    viewprovider = OpenEMSMaterialViewProvider()
    viewprovider.attach(_ViewObjectStub())

    assert viewprovider.claimChildren() == [geo_a, geo_b]


def test_material_viewprovider_propagates_visibility_to_assigned_geometry():
    from OpenEMSWorkbench.objects.material_feature import OpenEMSMaterialViewProvider

    geo_a = type("Geo", (), {"ViewObject": type("GeoView", (), {"Visibility": True})()})()
    geo_b = type("Geo", (), {"ViewObject": type("GeoView", (), {"Visibility": True})()})()

    material = type("Material", (), {"AssignedGeometry": [geo_a, geo_b]})()
    vobj = type("MaterialView", (), {"Object": material, "Visibility": True})()

    viewprovider = OpenEMSMaterialViewProvider()
    viewprovider.attach(vobj)

    vobj.Visibility = False
    viewprovider.onChanged(vobj, "Visibility")
    assert geo_a.ViewObject.Visibility is False
    assert geo_b.ViewObject.Visibility is False

    vobj.Visibility = True
    viewprovider.onChanged(vobj, "Visibility")
    assert geo_a.ViewObject.Visibility is True
    assert geo_b.ViewObject.Visibility is True
