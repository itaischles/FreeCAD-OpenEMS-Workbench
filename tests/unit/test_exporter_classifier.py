from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class Obj:
    def __init__(self, type_id, **attrs):
        self.TypeId = type_id
        for key, value in attrs.items():
            setattr(self, key, value)


def test_classifier_detects_box_and_cylinder_and_stl():
    from OpenEMSWorkbench.exporter.geometry_classifier import classify_geometry_object

    assert classify_geometry_object(Obj("Part::Box")) == "box"
    assert classify_geometry_object(Obj("Part::Cylinder")) == "cylinder"
    assert classify_geometry_object(Obj("Part::Feature")) == "stl"
