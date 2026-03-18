from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_excitation_visibility_defaults_to_gaussian():
    from OpenEMSWorkbench.gui.task_panels.simulation_panel import excitation_visibility_flags

    gaussian, sinusoid, custom = excitation_visibility_flags("")
    assert gaussian is True
    assert sinusoid is False
    assert custom is False


def test_excitation_visibility_selects_sinusoid_group():
    from OpenEMSWorkbench.gui.task_panels.simulation_panel import excitation_visibility_flags

    gaussian, sinusoid, custom = excitation_visibility_flags("Sinusoid")
    assert gaussian is False
    assert sinusoid is True
    assert custom is False


def test_excitation_visibility_selects_custom_group():
    from OpenEMSWorkbench.gui.task_panels.simulation_panel import excitation_visibility_flags

    gaussian, sinusoid, custom = excitation_visibility_flags("Custom")
    assert gaussian is False
    assert sinusoid is False
    assert custom is True


def test_excitation_visibility_accepts_legacy_aliases():
    from OpenEMSWorkbench.gui.task_panels.simulation_panel import excitation_visibility_flags

    gaussian, sinusoid, custom = excitation_visibility_flags("Sinusoidal")
    assert gaussian is False
    assert sinusoid is True
    assert custom is False

    gaussian, sinusoid, custom = excitation_visibility_flags("custom-expression")
    assert gaussian is False
    assert sinusoid is False
    assert custom is True
