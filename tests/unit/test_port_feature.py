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


def test_port_proxy_adds_waveguide_face_and_offset_properties_with_defaults():
    from OpenEMSWorkbench.objects.port_feature import OpenEMSPortProxy

    obj = FakeObject()
    proxy = OpenEMSPortProxy()
    proxy.ensure_properties(obj)

    assert obj.SimulationBoxFace == "ZMin"
    assert obj.SourcePlaneOffsetCells == 3

    assert obj._props["SimulationBoxFace"]["type"] == "App::PropertyEnumeration"
    assert obj._props["SimulationBoxFace"]["group"] == "Waveguide"
    assert obj._props["SourcePlaneOffsetCells"]["type"] == "App::PropertyInteger"
    assert obj._props["SourcePlaneOffsetCells"]["group"] == "Waveguide"


def test_port_proxy_ensure_properties_keeps_existing_waveguide_values():
    from OpenEMSWorkbench.objects.port_feature import OpenEMSPortProxy

    obj = FakeObject()
    proxy = OpenEMSPortProxy()

    proxy.ensure_properties(obj)
    obj.SimulationBoxFace = "XMax"
    obj.SourcePlaneOffsetCells = 5

    proxy.ensure_properties(obj)

    assert obj.SimulationBoxFace == "XMax"
    assert obj.SourcePlaneOffsetCells == 5
    assert list(obj._props).count("SimulationBoxFace") == 1
    assert list(obj._props).count("SourcePlaneOffsetCells") == 1


def test_compute_source_plane_uses_min_face_offset_cells():
    from OpenEMSWorkbench.meshing import MeshLines
    from OpenEMSWorkbench.objects.port_feature import _compute_source_plane_from_mesh

    mesh = MeshLines(
        coordinate_system="Cartesian",
        x=(0.0, 1.0, 2.0, 3.0, 4.0),
        y=(10.0, 12.0),
        z=(20.0, 25.0),
    )

    plane = _compute_source_plane_from_mesh(mesh, "XMin", 2)
    assert plane is not None
    assert plane["axis"] == "x"
    assert plane["coordinate"] == 2.0
    assert plane["ymin"] == 10.0
    assert plane["zmax"] == 25.0


def test_compute_source_plane_uses_max_face_offset_cells_and_clamps():
    from OpenEMSWorkbench.meshing import MeshLines
    from OpenEMSWorkbench.objects.port_feature import _compute_source_plane_from_mesh

    mesh = MeshLines(
        coordinate_system="Cartesian",
        x=(0.0, 1.0, 2.0),
        y=(0.0, 5.0),
        z=(0.0, 7.0),
    )

    plane = _compute_source_plane_from_mesh(mesh, "XMax", 99)
    assert plane is not None
    assert plane["axis"] == "x"
    assert plane["coordinate"] == 0.0


def test_compute_source_plane_rejects_non_cartesian_mesh():
    from OpenEMSWorkbench.meshing import MeshLines
    from OpenEMSWorkbench.objects.port_feature import _compute_source_plane_from_mesh

    mesh = MeshLines(
        coordinate_system="Cylindrical",
        x=(),
        y=(),
        z=(0.0, 1.0),
        radial=(0.0, 1.0),
    )

    plane = _compute_source_plane_from_mesh(mesh, "ZMin", 3)
    assert plane is None


def test_compute_three_plane_contract_for_min_face_uses_next_cell_for_reference():
    from OpenEMSWorkbench.meshing import MeshLines
    from OpenEMSWorkbench.objects.port_feature import _compute_waveguide_three_plane_contract

    mesh = MeshLines(
        coordinate_system="Cartesian",
        x=(0.0, 1.0, 2.0, 3.0, 4.0),
        y=(0.0, 1.0),
        z=(0.0, 1.0),
    )

    contract = _compute_waveguide_three_plane_contract(mesh, "XMin", 2)
    assert contract is not None
    assert contract["inward_direction"] == "+x"
    assert contract["source_offset_cells"] == 2
    assert contract["reference_offset_cells"] == 3
    assert contract["source_plane"]["coordinate"] == 2.0
    assert contract["reference_plane"]["coordinate"] == 3.0


def test_compute_three_plane_contract_for_max_face_uses_next_cell_inward():
    from OpenEMSWorkbench.meshing import MeshLines
    from OpenEMSWorkbench.objects.port_feature import _compute_waveguide_three_plane_contract

    mesh = MeshLines(
        coordinate_system="Cartesian",
        x=(0.0, 1.0, 2.0, 3.0, 4.0),
        y=(0.0, 1.0),
        z=(0.0, 1.0),
    )

    contract = _compute_waveguide_three_plane_contract(mesh, "XMax", 2)
    assert contract is not None
    assert contract["inward_direction"] == "-x"
    assert contract["source_plane"]["coordinate"] == 2.0
    assert contract["reference_plane"]["coordinate"] == 1.0


def test_source_plane_offset_normalization_clamps_to_range_2_to_9():
    from OpenEMSWorkbench.objects.port_feature import _normalized_source_plane_offset

    assert _normalized_source_plane_offset(1) == 2
    assert _normalized_source_plane_offset(2) == 2
    assert _normalized_source_plane_offset(9) == 9
    assert _normalized_source_plane_offset(10) == 9


def test_port_proxy_normalizes_source_plane_offset_property_on_ensure():
    from OpenEMSWorkbench.objects.port_feature import OpenEMSPortProxy

    obj = FakeObject()
    proxy = OpenEMSPortProxy()
    proxy.ensure_properties(obj)

    obj.SourcePlaneOffsetCells = 1
    proxy.ensure_properties(obj)
    assert obj.SourcePlaneOffsetCells == 2

    obj.SourcePlaneOffsetCells = 50
    proxy.ensure_properties(obj)
    assert obj.SourcePlaneOffsetCells == 9


def test_port_proxy_on_changed_does_not_crash_when_restore_flag_missing():
    from OpenEMSWorkbench.objects.port_feature import OpenEMSPortProxy

    obj = FakeObject()
    proxy = OpenEMSPortProxy()
    proxy.ensure_properties(obj)

    # Simulate restore edge case where legacy proxy instance lacks base init state.
    if hasattr(proxy, "_is_restoring"):
        delattr(proxy, "_is_restoring")

    proxy.onChanged(obj, "SourcePlaneOffsetCells")
    assert 2 <= obj.SourcePlaneOffsetCells <= 9


def test_port_proxy_on_changed_normalizes_offset_without_preview_refresh_side_effect():
    from OpenEMSWorkbench.objects.port_feature import OpenEMSPortProxy

    obj = FakeObject()
    proxy = OpenEMSPortProxy()
    proxy.ensure_properties(obj)

    calls = {"count": 0}

    def _unexpected_preview_refresh(_obj):
        calls["count"] += 1

    proxy._refresh_waveguide_preview = _unexpected_preview_refresh
    obj.SourcePlaneOffsetCells = 99

    proxy.onChanged(obj, "SourcePlaneOffsetCells")

    assert obj.SourcePlaneOffsetCells == 9
    assert calls["count"] == 0


def test_waveguide_preview_overlay_definition_uses_selected_propagation_direction():
    from OpenEMSWorkbench.objects.port_feature import _waveguide_preview_overlay_definition

    plane = {
        "axis": "z",
        "coordinate": 2.0,
        "xmin": 0.0,
        "xmax": 20.0,
        "ymin": -10.0,
        "ymax": 10.0,
        "zmin": 0.0,
        "zmax": 10.0,
    }

    overlay = _waveguide_preview_overlay_definition(plane, "+z", None)

    assert overlay["center"] == (10.0, 0.0, 2.0)
    assert overlay["arrow_direction"] == (0.0, 0.0, 1.0)
    assert overlay["arrow_length"] == 4.0
    assert overlay["circles"] == []


def test_waveguide_preview_overlay_definition_adds_coax_circles_when_supported():
    from OpenEMSWorkbench.objects.port_feature import _waveguide_preview_overlay_definition

    plane = {
        "axis": "z",
        "coordinate": 0.0,
        "xmin": -60.0,
        "xmax": 60.0,
        "ymin": -60.0,
        "ymax": 60.0,
        "zmin": 0.0,
        "zmax": 100.0,
    }
    detection = {
        "status": "supported",
        "inner": {"radius": 10.0, "center": [0.1, -0.2, 50.0]},
        "outer": {"radius": 55.0, "center": [0.3, 0.0, 50.0]},
    }

    overlay = _waveguide_preview_overlay_definition(plane, "+z", detection)

    assert len(overlay["circles"]) == 2
    assert overlay["circles"][0]["radius"] == 10.0
    assert overlay["circles"][1]["radius"] == 55.0
    assert overlay["circles"][0]["center"] == (0.2, -0.1, 0.0)
    assert overlay["circles"][0]["normal"] == (0.0, 0.0, 1.0)


def test_port_viewprovider_claims_waveguide_preview_helper_child():
    from OpenEMSWorkbench.objects.port_feature import OpenEMSPortProxy, OpenEMSPortViewProvider

    class _Doc:
        def __init__(self, objects):
            self.Objects = objects

    port_obj = type("Port", (), {"Name": "Port1"})()
    proxy = OpenEMSPortProxy()
    port_obj.Proxy = proxy

    preview = type(
        "Preview",
        (),
        {
            "OpenEMSWaveguidePortPlane": True,
            "OpenEMSWaveguidePortName": "Port1",
        },
    )()
    port_obj.Document = _Doc([preview])

    viewprovider = OpenEMSPortViewProvider()
    viewprovider.attach(type("ViewObj", (), {"Object": port_obj})())

    assert viewprovider.claimChildren() == [preview]