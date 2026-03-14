from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_phase2_model_has_expected_groups():
    from OpenEMSWorkbench import model

    assert "simulation" in model.DEFAULTS
    assert "material" in model.DEFAULTS
    assert "boundary" in model.DEFAULTS
    assert "port" in model.DEFAULTS
    assert "grid" in model.DEFAULTS
    assert "dumpbox" in model.DEFAULTS


def test_coordinate_and_port_enums_are_defined():
    from OpenEMSWorkbench import model

    assert "Cartesian" in model.COORDINATE_SYSTEMS
    assert "Cylindrical" in model.COORDINATE_SYSTEMS
    assert "Lumped" in model.PORT_TYPES
    assert "Waveguide" in model.PORT_TYPES
