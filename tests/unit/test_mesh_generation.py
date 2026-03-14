from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class _GridStub:
    def __init__(
        self,
        coordinate_system="Cartesian",
        base_resolution=1.0,
        max_resolution=5.0,
        grading_factor=1.3,
        auto_smooth=True,
    ):
        self.CoordinateSystem = coordinate_system
        self.BaseResolution = base_resolution
        self.MaxResolution = max_resolution
        self.GradingFactor = grading_factor
        self.AutoSmooth = auto_smooth


class _ProxyStub:
    TYPE = "OpenEMS_Grid"


class _AnalysisProxyStub:
    TYPE = "OpenEMS_Analysis"


class _MemberStub:
    def __init__(self):
        self.Proxy = _ProxyStub()


class _AnalysisStub:
    def __init__(self, members=None):
        self.Proxy = _AnalysisProxyStub()
        self.Group = members or []
        self.IsActive = True


class _DocStub:
    def __init__(self, analyses):
        self.Objects = analyses


def _is_monotonic_non_decreasing(values):
    return all(left <= right for left, right in zip(values, values[1:]))


def test_cartesian_mesh_axes_are_monotonic_and_centered():
    from OpenEMSWorkbench.meshing import generate_mesh_from_grid

    mesh = generate_mesh_from_grid(_GridStub(coordinate_system="Cartesian"))

    assert mesh.coordinate_system == "Cartesian"
    assert mesh.x
    assert mesh.y
    assert mesh.z
    assert _is_monotonic_non_decreasing(mesh.x)
    assert _is_monotonic_non_decreasing(mesh.y)
    assert _is_monotonic_non_decreasing(mesh.z)
    assert 0.0 in mesh.x
    assert 0.0 in mesh.y
    assert 0.0 in mesh.z


def test_cylindrical_mesh_axes_are_monotonic_and_have_azimuth():
    from OpenEMSWorkbench.meshing import generate_mesh_from_grid

    mesh = generate_mesh_from_grid(_GridStub(coordinate_system="Cylindrical"))

    assert mesh.coordinate_system == "Cylindrical"
    assert mesh.radial
    assert mesh.azimuth
    assert mesh.z
    assert _is_monotonic_non_decreasing(mesh.radial)
    assert _is_monotonic_non_decreasing(mesh.z)
    assert mesh.radial[0] == 0.0


def test_mesh_generation_is_deterministic_for_same_input():
    from OpenEMSWorkbench.meshing import generate_mesh_from_grid

    grid = _GridStub(coordinate_system="Cartesian", base_resolution=0.8, max_resolution=3.5)
    mesh_a = generate_mesh_from_grid(grid)
    mesh_b = generate_mesh_from_grid(grid)

    assert mesh_a.signature == mesh_b.signature
    assert mesh_a.x == mesh_b.x
    assert mesh_a.y == mesh_b.y
    assert mesh_a.z == mesh_b.z


def test_mesh_generation_normalizes_invalid_parameters():
    from OpenEMSWorkbench.meshing import generate_mesh_from_grid

    mesh = generate_mesh_from_grid(
        _GridStub(
            coordinate_system="Cartesian",
            base_resolution=-1.0,
            max_resolution=0.0,
            grading_factor=0.2,
            auto_smooth=False,
        )
    )

    assert mesh.x
    assert mesh.y
    assert mesh.z
    assert _is_monotonic_non_decreasing(mesh.x)


def test_resolve_active_analysis_grid_returns_assigned_grid():
    from OpenEMSWorkbench.meshing import resolve_active_analysis_grid

    grid = _MemberStub()
    analysis = _AnalysisStub(members=[grid])
    doc = _DocStub([analysis])

    resolved_analysis, resolved_grid = resolve_active_analysis_grid(doc)
    assert resolved_analysis is analysis
    assert resolved_grid is grid
