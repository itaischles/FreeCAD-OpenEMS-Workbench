from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def _segment_axis_constants(segment):
    (x1, y1, z1), (x2, y2, z2) = segment
    return (
        x1 == x2,
        y1 == y2,
        z1 == z2,
    )


def test_sample_axis_preserves_endpoints_and_is_deterministic():
    from OpenEMSWorkbench.visualization import _sample_axis

    axis = tuple(float(i) for i in range(100))
    sample_a = _sample_axis(axis, 10)
    sample_b = _sample_axis(axis, 10)

    assert sample_a == sample_b
    assert sample_a[0] == 0.0
    assert sample_a[-1] == 99.0
    assert len(sample_a) <= 10


def test_build_cartesian_segments_contains_three_plane_orientations():
    from OpenEMSWorkbench.meshing import MeshLines
    from OpenEMSWorkbench.visualization import _build_cartesian_segments

    mesh = MeshLines(
        coordinate_system="Cartesian",
        x=tuple(float(v) for v in range(0, 11)),
        y=tuple(float(v) for v in range(0, 11)),
        z=tuple(float(v) for v in range(0, 11)),
    )

    segments = _build_cartesian_segments(mesh)
    assert segments

    has_xy_like = False
    has_xz_like = False
    has_yz_like = False

    for segment in segments:
        if len(segment) != 2:
            continue
        x_const, y_const, z_const = _segment_axis_constants(segment)
        if z_const and (not x_const or not y_const):
            has_xy_like = True
        if y_const and (not x_const or not z_const):
            has_xz_like = True
        if x_const and (not y_const or not z_const):
            has_yz_like = True

    assert has_xy_like
    assert has_xz_like
    assert has_yz_like


def test_build_cartesian_segments_decimates_dense_axes():
    from OpenEMSWorkbench.meshing import MeshLines
    from OpenEMSWorkbench.visualization import _build_cartesian_segments

    dense_axis = tuple(float(v) for v in range(0, 401))
    mesh = MeshLines(
        coordinate_system="Cartesian",
        x=dense_axis,
        y=dense_axis,
        z=dense_axis,
    )

    segments = _build_cartesian_segments(mesh)

    # If decimation is active, segment count should stay below naive full-grid rendering.
    assert len(segments) < 1000


def test_build_cartesian_segments_respects_preview_line_cap():
    from OpenEMSWorkbench.meshing import MeshLines
    from OpenEMSWorkbench.visualization import _build_cartesian_segments

    dense_axis = tuple(float(v) for v in range(0, 401))
    mesh_low = MeshLines(
        coordinate_system="Cartesian",
        x=dense_axis,
        y=dense_axis,
        z=dense_axis,
        preview_line_cap=12,
    )
    mesh_high = MeshLines(
        coordinate_system="Cartesian",
        x=dense_axis,
        y=dense_axis,
        z=dense_axis,
        preview_line_cap=96,
    )

    segments_low = _build_cartesian_segments(mesh_low)
    segments_high = _build_cartesian_segments(mesh_high)

    assert len(segments_high) > len(segments_low)
