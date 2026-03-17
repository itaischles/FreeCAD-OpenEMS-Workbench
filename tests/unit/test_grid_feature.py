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
