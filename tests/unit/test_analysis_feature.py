from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class AnalysisObj:
    def __init__(self):
        self._props = {}

    def addProperty(self, prop_type, prop_name, group, description):
        self._props[prop_name] = {
            "type": prop_type,
            "group": group,
            "description": description,
        }


def test_analysis_proxy_refreshes_simulation_box_on_group_change(monkeypatch):
    from OpenEMSWorkbench.objects.analysis_feature import OpenEMSAnalysisProxy

    calls = []

    def _fake_refresh(analysis):
        calls.append(analysis)
        return {}

    monkeypatch.setattr(
        "OpenEMSWorkbench.exporter.document_reader.refresh_simulation_box_for_analysis",
        _fake_refresh,
    )

    proxy = OpenEMSAnalysisProxy()
    analysis = AnalysisObj()
    proxy.attach(analysis)

    proxy.onChanged(analysis, "Group")

    assert calls == [analysis]


def test_analysis_proxy_skips_refresh_while_restoring(monkeypatch):
    from OpenEMSWorkbench.objects.analysis_feature import OpenEMSAnalysisProxy

    calls = []

    def _fake_refresh(analysis):
        calls.append(analysis)
        return {}

    monkeypatch.setattr(
        "OpenEMSWorkbench.exporter.document_reader.refresh_simulation_box_for_analysis",
        _fake_refresh,
    )

    proxy = OpenEMSAnalysisProxy()
    analysis = AnalysisObj()
    proxy.attach(analysis)
    proxy._is_restoring = True

    proxy.onChanged(analysis, "Group")

    assert calls == []


def test_analysis_proxy_skips_refresh_when_group_refresh_is_suppressed(monkeypatch):
    from OpenEMSWorkbench.objects.analysis_feature import OpenEMSAnalysisProxy

    calls = []

    def _fake_refresh(analysis):
        calls.append(analysis)
        return {}

    monkeypatch.setattr(
        "OpenEMSWorkbench.exporter.document_reader.refresh_simulation_box_for_analysis",
        _fake_refresh,
    )

    proxy = OpenEMSAnalysisProxy()
    analysis = AnalysisObj()
    analysis._openems_skip_group_refresh = True
    proxy.attach(analysis)

    proxy.onChanged(analysis, "Group")

    assert calls == []


def test_analysis_viewprovider_claims_group_children_for_tree_nesting():
    from OpenEMSWorkbench.objects.analysis_feature import OpenEMSAnalysisViewProvider

    child_a = object()
    child_b = object()

    class _ViewObjectStub:
        def __init__(self):
            self.Object = type("Analysis", (), {"Group": [child_a, child_b]})()

    viewprovider = OpenEMSAnalysisViewProvider()
    viewprovider.attach(_ViewObjectStub())

    assert viewprovider.claimChildren() == [child_a, child_b]
