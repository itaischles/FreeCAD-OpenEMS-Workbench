from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class Proxy:
    def __init__(self, proxy_type):
        self.TYPE = proxy_type


class Obj:
    def __init__(self, name, proxy_type, is_active=False):
        self.Name = name
        self.Label = name
        self.Proxy = Proxy(proxy_type)
        self.IsActive = is_active


class AnalysisObj(Obj):
    def __init__(self, name, is_active=False):
        super().__init__(name, "OpenEMS_Analysis", is_active=is_active)
        self.Group = []

    def addObject(self, member):
        self.Group.append(member)


class Doc:
    def __init__(self, objects):
        self.Objects = objects


def test_active_analysis_detection_and_switching():
    from OpenEMSWorkbench.utils.analysis_context import (
        get_active_analysis,
        set_active_analysis,
    )

    a1 = AnalysisObj("A1", is_active=True)
    a2 = AnalysisObj("A2", is_active=False)
    doc = Doc([a1, a2])

    assert get_active_analysis(doc) is a1
    set_active_analysis(doc, a2)
    assert get_active_analysis(doc) is a2
    assert a1.IsActive is False
    assert a2.IsActive is True


def test_add_member_to_analysis_filters_non_openems():
    from OpenEMSWorkbench.utils.analysis_context import add_member_to_analysis

    analysis = AnalysisObj("Analysis")
    good = Obj("Mat", "OpenEMS_Material")
    bad = Obj("Cube", "Part::Feature")

    assert add_member_to_analysis(analysis, good) is True
    assert add_member_to_analysis(analysis, good) is False
    assert add_member_to_analysis(analysis, bad) is False
    assert analysis.Group == [good]


def test_assign_members_to_analysis_detailed_counts_states():
    from OpenEMSWorkbench.utils.analysis_context import assign_members_to_analysis_detailed

    analysis = AnalysisObj("Analysis")
    already = Obj("Already", "OpenEMS_Material")
    analysis.addObject(already)

    new_member = Obj("New", "OpenEMS_Port")
    ignored = Obj("Ignored", "Part::Feature")

    result = assign_members_to_analysis_detailed(analysis, [already, new_member, ignored])

    assert result["added"] == 1
    assert result["already_member"] == 1
    assert result["ignored"] == 1
