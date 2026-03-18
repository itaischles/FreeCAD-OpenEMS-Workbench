from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class MeshStub:
    def __init__(self, coordinate_system, x=(), y=(), z=(), radial=()):
        self.coordinate_system = coordinate_system
        self.x = tuple(x)
        self.y = tuple(y)
        self.z = tuple(z)
        self.radial = tuple(radial)


def test_compute_cfl_timestep_seconds_cartesian_returns_positive_value():
    from OpenEMSWorkbench.utils.timestep_budget import compute_cfl_timestep_seconds

    mesh = MeshStub(
        coordinate_system="Cartesian",
        x=(0.0, 1.0, 2.0),
        y=(0.0, 1.0, 2.0),
        z=(0.0, 1.0, 2.0),
    )

    dt = compute_cfl_timestep_seconds(mesh, delta_unit_meters=1e-3)
    assert dt > 0.0


def test_compute_timestep_budget_returns_expected_nrts_for_simple_case():
    from OpenEMSWorkbench.utils.timestep_budget import compute_timestep_budget

    mesh = MeshStub(
        coordinate_system="Cartesian",
        x=(0.0, 1.0, 2.0),
        y=(0.0, 1.0, 2.0),
        z=(0.0, 1.0, 2.0),
    )

    dt, nr_ts = compute_timestep_budget(
        mesh,
        delta_unit_meters=1e-3,
        max_time_sec=100e-9,
    )
    assert dt > 0.0
    assert nr_ts >= 1


def test_compute_number_of_time_steps_uses_ceil():
    from OpenEMSWorkbench.utils.timestep_budget import compute_number_of_time_steps

    assert compute_number_of_time_steps(max_time_sec=1.0, dt_sec=0.3) == 4


def test_format_int_scientific_helper_outputs_expected_notation():
    from OpenEMSWorkbench.objects.simulation_feature import _format_int_scientific

    assert _format_int_scientific(0) == "0"
    assert _format_int_scientific(1234567).startswith("1.234567e")
