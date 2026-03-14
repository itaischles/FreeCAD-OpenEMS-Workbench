from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class _Proxy:
    def __init__(self, proxy_type: str):
        self.TYPE = proxy_type


class _Obj:
    def __init__(self, proxy_type: str):
        self.Proxy = _Proxy(proxy_type)


def test_registry_resolves_known_proxy_types():
    from OpenEMSWorkbench.gui.task_panels.panel_registry import get_panel_class_for_object

    assert get_panel_class_for_object(_Obj("OpenEMS_Simulation")) is not None
    assert get_panel_class_for_object(_Obj("OpenEMS_Material")) is not None
    assert get_panel_class_for_object(_Obj("OpenEMS_Boundary")) is not None
    assert get_panel_class_for_object(_Obj("OpenEMS_Port")) is not None
    assert get_panel_class_for_object(_Obj("OpenEMS_Grid")) is not None
    assert get_panel_class_for_object(_Obj("OpenEMS_DumpBox")) is not None


def test_registry_returns_none_for_unknown_proxy_type():
    from OpenEMSWorkbench.gui.task_panels.panel_registry import get_panel_class_for_object

    assert get_panel_class_for_object(_Obj("Unknown_Type")) is None
