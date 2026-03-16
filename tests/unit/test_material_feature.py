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
