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


def test_add_property_if_missing_is_idempotent():
    from OpenEMSWorkbench.objects.base_feature import add_property_if_missing

    obj = FakeObject()
    add_property_if_missing(
        obj,
        "App::PropertyFloat",
        "TestProp",
        "Test",
        "A property",
        1.0,
    )
    add_property_if_missing(
        obj,
        "App::PropertyFloat",
        "TestProp",
        "Test",
        "A property",
        2.0,
    )

    assert "TestProp" in obj._props
    assert obj.TestProp == 1.0
    assert len(obj._props) == 1


def test_set_enum_choices_preserves_existing_value_when_possible():
    from OpenEMSWorkbench.objects.base_feature import set_enum_choices

    obj = FakeObject()
    obj.Mode = "B"
    set_enum_choices(obj, "Mode", ["A", "B", "C"], "A")
    assert obj.Mode == "B"

    obj2 = FakeObject()
    obj2.Mode = "Z"
    set_enum_choices(obj2, "Mode", ["A", "B", "C"], "A")
    assert obj2.Mode == "A"


class FakeViewObject:
    def __init__(self):
        self.Object = object()


def test_viewprovider_attach_sets_proxy():
    from OpenEMSWorkbench.objects.base_feature import ViewProviderBase

    view = FakeViewObject()
    vp = ViewProviderBase()
    vp.attach(view)
    assert view.Proxy is vp


def test_viewprovider_base_reports_default_display_mode():
    from OpenEMSWorkbench.objects.base_feature import ViewProviderBase

    vp = ViewProviderBase()

    assert vp.getDisplayModes(object()) == ["Default"]
    assert vp.getDefaultDisplayMode() == "Default"
