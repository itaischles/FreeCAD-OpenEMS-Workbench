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
    assert "Gaussian" in model.EXCITATION_TYPES
    assert "Sinusoid" in model.EXCITATION_TYPES
    assert "Custom" in model.EXCITATION_TYPES
    assert model.DUMP_TYPES == ["EField"]


def test_excitation_and_port_region_defaults_exist():
    from OpenEMSWorkbench import model

    sim_defaults = model.DEFAULTS["simulation"]
    port_defaults = model.DEFAULTS["port"]

    assert sim_defaults["excitation_type"] == "Gaussian"
    assert sim_defaults["excitation_f_max"] > 0.0
    assert sim_defaults["max_simulation_time"] > 0.0
    assert sim_defaults["excitation_f0"] > 0.0
    assert sim_defaults["excitation_fc"] > 0.0
    assert sim_defaults["sinusoid_frequency"] > 0.0
    assert sim_defaults["gaussian_sigma"] > 0.0
    assert sim_defaults["gaussian_delay"] >= 0.0
    assert port_defaults["propagation_direction"] == "+z"
    assert "start_x" in port_defaults
    assert "stop_z" in port_defaults
