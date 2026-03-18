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
        preview_line_cap=96,
    ):
        self.CoordinateSystem = coordinate_system
        self.MeshBaseStep = base_resolution
        self.MeshMaxStep = max_resolution
        self.MeshGrowthRate = grading_factor
        self.MeshAutoSmooth = auto_smooth
        self.MeshPreviewLineCap = preview_line_cap


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
        self.Document = None


class _VectorStub:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class _PlacementStub:
    def __init__(self, base):
        self.Base = base


class _SimulationBoxStub:
    def __init__(self, start_x, start_y, start_z, length, width, height):
        self.OpenEMSSimulationBox = True
        self.Length = length
        self.Width = width
        self.Height = height
        self.Placement = _PlacementStub(_VectorStub(start_x, start_y, start_z))


class _BoundBoxStub:
    def __init__(self, xmin, ymin, zmin, xmax, ymax, zmax):
        self.XMin = xmin
        self.YMin = ymin
        self.ZMin = zmin
        self.XMax = xmax
        self.YMax = ymax
        self.ZMax = zmax


class _ShapeStub:
    def __init__(self, bounds):
        self.BoundBox = bounds


class _GeometryStub:
    def __init__(self, name, xmin, ymin, zmin, xmax, ymax, zmax):
        self.Name = name
        self.Shape = _ShapeStub(_BoundBoxStub(xmin, ymin, zmin, xmax, ymax, zmax))


class _DocStub:
    def __init__(self, analyses):
        self.Objects = analyses


def _is_monotonic_non_decreasing(values):
    return all(left <= right for left, right in zip(values, values[1:]))


_DEFAULT_EXTENTS = (-10.0, 10.0, -10.0, 10.0, -10.0, 10.0)


def test_cartesian_mesh_axes_are_monotonic_and_bounded():
    from OpenEMSWorkbench.meshing import generate_mesh_from_grid

    mesh = generate_mesh_from_grid(
        _GridStub(coordinate_system="Cartesian"),
        simulation_box_extents=_DEFAULT_EXTENTS,
    )

    assert mesh.coordinate_system == "Cartesian"
    assert mesh.x
    assert mesh.y
    assert mesh.z
    assert _is_monotonic_non_decreasing(mesh.x)
    assert _is_monotonic_non_decreasing(mesh.y)
    assert _is_monotonic_non_decreasing(mesh.z)
    assert mesh.x[0] == -10.0 and mesh.x[-1] == 10.0
    assert mesh.y[0] == -10.0 and mesh.y[-1] == 10.0
    assert mesh.z[0] == -10.0 and mesh.z[-1] == 10.0


def test_cylindrical_mesh_axes_are_monotonic_and_have_azimuth():
    from OpenEMSWorkbench.meshing import generate_mesh_from_grid

    mesh = generate_mesh_from_grid(
        _GridStub(coordinate_system="Cylindrical"),
        simulation_box_extents=_DEFAULT_EXTENTS,
    )

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
    mesh_a = generate_mesh_from_grid(grid, simulation_box_extents=_DEFAULT_EXTENTS)
    mesh_b = generate_mesh_from_grid(grid, simulation_box_extents=_DEFAULT_EXTENTS)

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
        ),
        simulation_box_extents=_DEFAULT_EXTENTS,
    )

    assert mesh.x
    assert mesh.y
    assert mesh.z
    assert _is_monotonic_non_decreasing(mesh.x)


def test_mesh_generation_respects_simulation_box_extents_for_cartesian_axes():
    from OpenEMSWorkbench.meshing import generate_mesh_from_grid

    mesh = generate_mesh_from_grid(
        _GridStub(coordinate_system="Cartesian", base_resolution=1.0, max_resolution=2.0),
        simulation_box_extents=(-2.0, 3.0, 1.0, 6.0, -1.0, 4.0),
    )

    assert mesh.x[0] == -2.0
    assert mesh.x[-1] == 3.0
    assert mesh.y[0] == 1.0
    assert mesh.y[-1] == 6.0
    assert mesh.z[0] == -1.0
    assert mesh.z[-1] == 4.0
    assert _is_monotonic_non_decreasing(mesh.x)
    assert _is_monotonic_non_decreasing(mesh.y)
    assert _is_monotonic_non_decreasing(mesh.z)
    assert all(-2.0 <= value <= 3.0 for value in mesh.x)
    assert all(1.0 <= value <= 6.0 for value in mesh.y)
    assert all(-1.0 <= value <= 4.0 for value in mesh.z)


def test_mesh_generation_carries_preview_line_cap_from_grid():
    from OpenEMSWorkbench.meshing import generate_mesh_from_grid

    mesh = generate_mesh_from_grid(
        _GridStub(preview_line_cap=123),
        simulation_box_extents=_DEFAULT_EXTENTS,
    )
    assert mesh.preview_line_cap == 123


def test_resolve_active_analysis_grid_returns_assigned_grid():
    from OpenEMSWorkbench.meshing import resolve_active_analysis_grid

    grid = _MemberStub()
    analysis = _AnalysisStub(members=[grid])
    doc = _DocStub([analysis])

    resolved_analysis, resolved_grid = resolve_active_analysis_grid(doc)
    assert resolved_analysis is analysis
    assert resolved_grid is grid


def test_build_mesh_for_active_analysis_uses_simulation_box_object_extents():
    from OpenEMSWorkbench.meshing import build_mesh_for_active_analysis

    grid = _MemberStub()
    grid.MeshBaseStep = 1.0
    grid.MeshMaxStep = 2.0
    grid.MeshGrowthRate = 1.2
    grid.MeshAutoSmooth = True
    grid.CoordinateSystem = "Cartesian"

    simulation_box = _SimulationBoxStub(
        start_x=10.0,
        start_y=20.0,
        start_z=30.0,
        length=5.0,
        width=6.0,
        height=7.0,
    )

    analysis = _AnalysisStub(members=[grid, simulation_box])
    doc = _DocStub([analysis])

    _, _, mesh = build_mesh_for_active_analysis(doc)
    assert mesh.x[0] == 10.0
    assert mesh.x[-1] == 15.0
    assert mesh.y[0] == 20.0
    assert mesh.y[-1] == 26.0
    assert mesh.z[0] == 30.0
    assert mesh.z[-1] == 37.0


def test_build_mesh_for_active_analysis_snaps_to_geometry_bounding_faces():
    from OpenEMSWorkbench.meshing import build_mesh_for_active_analysis

    grid = _MemberStub()
    grid.MeshBaseStep = 2.0
    grid.MeshMaxStep = 2.0
    grid.MeshGrowthRate = 1.0
    grid.MeshAutoSmooth = False
    grid.MeshPreviewLineCap = 5
    grid.CoordinateSystem = "Cartesian"

    simulation_box = _SimulationBoxStub(
        start_x=0.0,
        start_y=0.0,
        start_z=0.0,
        length=10.0,
        width=10.0,
        height=10.0,
    )
    geometry = _GeometryStub("GeoA", 1.3, 2.1, 3.2, 4.7, 5.9, 8.8)

    analysis = _AnalysisStub(members=[grid, simulation_box, geometry])
    doc = _DocStub([analysis])

    _, _, mesh = build_mesh_for_active_analysis(doc)
    assert mesh.preview_line_cap == 5
    assert 1.3 in mesh.x and 4.7 in mesh.x
    assert 2.1 in mesh.y and 5.9 in mesh.y
    assert 3.2 in mesh.z and 8.8 in mesh.z


def test_build_mesh_for_active_analysis_clips_snaps_to_simulation_box():
    from OpenEMSWorkbench.meshing import build_mesh_for_active_analysis

    grid = _MemberStub()
    grid.MeshBaseStep = 2.0
    grid.MeshMaxStep = 2.0
    grid.MeshGrowthRate = 1.0
    grid.MeshAutoSmooth = False
    grid.CoordinateSystem = "Cartesian"

    simulation_box = _SimulationBoxStub(
        start_x=0.0,
        start_y=0.0,
        start_z=0.0,
        length=10.0,
        width=10.0,
        height=10.0,
    )
    geometry_outside = _GeometryStub("GeoOutside", -5.0, -4.0, -3.0, 12.0, 14.0, 15.0)

    analysis = _AnalysisStub(members=[grid, simulation_box, geometry_outside])
    doc = _DocStub([analysis])

    _, _, mesh = build_mesh_for_active_analysis(doc)
    assert all(0.0 <= value <= 10.0 for value in mesh.x)
    assert all(0.0 <= value <= 10.0 for value in mesh.y)
    assert all(0.0 <= value <= 10.0 for value in mesh.z)


def test_build_mesh_for_active_analysis_merges_near_duplicate_snap_lines():
    from OpenEMSWorkbench.meshing import build_mesh_for_active_analysis

    grid = _MemberStub()
    grid.MeshBaseStep = 1.0
    grid.MeshMaxStep = 1.0
    grid.MeshGrowthRate = 1.0
    grid.MeshAutoSmooth = False
    grid.CoordinateSystem = "Cartesian"

    simulation_box = _SimulationBoxStub(
        start_x=0.0,
        start_y=0.0,
        start_z=0.0,
        length=10.0,
        width=10.0,
        height=10.0,
    )
    # Near-coincident x faces differing by 4e-7 model units should be merged.
    geometry_a = _GeometryStub("GeoA", 2.0000000, 1.0, 1.0, 4.0, 2.0, 2.0)
    geometry_b = _GeometryStub("GeoB", 2.0000004, 3.0, 3.0, 5.0, 4.0, 4.0)

    analysis = _AnalysisStub(members=[grid, simulation_box, geometry_a, geometry_b])
    doc = _DocStub([analysis])

    _, _, mesh = build_mesh_for_active_analysis(doc)
    close_values = [value for value in mesh.x if abs(value - 2.0) < 1e-5]
    assert len(close_values) == 1
