from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class _BoundBox:
    def __init__(self, xmin, ymin, zmin, xmax, ymax, zmax):
        self.XMin = xmin
        self.YMin = ymin
        self.ZMin = zmin
        self.XMax = xmax
        self.YMax = ymax
        self.ZMax = zmax


class _Shape:
    def __init__(self):
        self.BoundBox = _BoundBox(0.0, 0.0, 0.0, 10.0, 20.0, 30.0)


class _Box:
    def __init__(self):
        self.Shape = _Shape()


class _Point:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class _Face:
    def __init__(self, x, y, z):
        self.CenterOfMass = _Point(x, y, z)


def test_boundary_property_for_selected_face_uses_face_center_geometry():
    from OpenEMSWorkbench.commands.object_commands import _boundary_property_for_selected_face

    box = _Box()

    assert _boundary_property_for_selected_face(box, "Face1", _Face(0.01, 10.0, 10.0)) == "BoundaryXMin"
    assert _boundary_property_for_selected_face(box, "Face1", _Face(9.99, 10.0, 10.0)) == "BoundaryXMax"
    assert _boundary_property_for_selected_face(box, "Face1", _Face(5.0, 0.02, 10.0)) == "BoundaryYMin"
    assert _boundary_property_for_selected_face(box, "Face1", _Face(5.0, 19.98, 10.0)) == "BoundaryYMax"
    assert _boundary_property_for_selected_face(box, "Face1", _Face(5.0, 10.0, 0.02)) == "BoundaryZMin"
    assert _boundary_property_for_selected_face(box, "Face1", _Face(5.0, 10.0, 29.98)) == "BoundaryZMax"


def test_boundary_property_for_selected_face_falls_back_to_face_name_map():
    from OpenEMSWorkbench.commands.object_commands import _boundary_property_for_selected_face

    box = _Box()

    assert _boundary_property_for_selected_face(box, "Face1", None) == "BoundaryZMin"
    assert _boundary_property_for_selected_face(box, "Face2", None) == "BoundaryZMax"
    assert _boundary_property_for_selected_face(box, "Face5", None) == "BoundaryXMin"
    assert _boundary_property_for_selected_face(box, "Face6", None) == "BoundaryXMax"
