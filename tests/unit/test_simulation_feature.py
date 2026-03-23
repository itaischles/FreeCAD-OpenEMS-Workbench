from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


class FakeObject:
    def __init__(self):
        self._props = {}
        self._editor_modes = {}

    def addProperty(self, prop_type, prop_name, group, description):
        self._props[prop_name] = {
            "type": prop_type,
            "group": group,
            "description": description,
        }

    def setEditorMode(self, prop_name, mode):
        self._editor_modes[prop_name] = mode


def test_simulation_proxy_adds_task_8_1_excitation_properties():
    from OpenEMSWorkbench.objects.simulation_feature import OpenEMSSimulationProxy

    obj = FakeObject()
    proxy = OpenEMSSimulationProxy()
    proxy.ensure_properties(obj)

    assert obj.ExcitationType == "Gaussian"
    assert obj.ExcitationFMax > 0.0
    assert obj.MaxSimulationTime > 0.0
    assert hasattr(obj, "ComputedTimeStep")
    assert hasattr(obj, "MaxSimulationTimeDisplay")
    assert hasattr(obj, "ComputedTimeStepDisplay")
    assert hasattr(obj, "ComputedNumberOfTimeSteps")
    assert hasattr(obj, "TimeStepBudgetStatus")
    assert hasattr(obj, "ComputedNumberOfTimeStepsRaw")
    assert hasattr(obj, "ComputedNumberOfTimeStepsScientific")
    assert hasattr(obj, "ComputedLengthUnitName")
    assert obj.SinusoidFrequency > 0.0
    assert obj.GaussianSigma > 0.0

    assert obj._props["ExcitationFMax"]["type"] == "App::PropertyFloat"
    assert obj._props["MaxSimulationTime"]["type"] == "App::PropertyFloat"
    assert obj._props["MaxSimulationTimeDisplay"]["type"] == "App::PropertyString"
    assert obj._props["ComputedTimeStep"]["type"] == "App::PropertyFloat"
    assert obj._props["ComputedTimeStepDisplay"]["type"] == "App::PropertyString"
    assert obj._props["ComputedNumberOfTimeSteps"]["type"] == "App::PropertyInteger"
    assert obj._props["TimeStepBudgetStatus"]["type"] == "App::PropertyString"
    assert obj._props["ComputedNumberOfTimeStepsRaw"]["type"] == "App::PropertyString"
    assert obj._props["ComputedNumberOfTimeStepsScientific"]["type"] == "App::PropertyString"
    assert obj._props["ComputedLengthUnitName"]["type"] == "App::PropertyString"
    assert obj._props["SinusoidFrequency"]["type"] == "App::PropertyFloat"
    assert obj._props["GaussianSigma"]["type"] == "App::PropertyFloat"
    assert obj._props["GaussianDelay"]["type"] == "App::PropertyFloat"
    assert obj._props["CustomExcitationExpression"]["type"] == "App::PropertyString"


def test_simulation_proxy_ensure_properties_keeps_existing_task_8_1_values():
    from OpenEMSWorkbench.objects.simulation_feature import OpenEMSSimulationProxy

    obj = FakeObject()
    proxy = OpenEMSSimulationProxy()
    proxy.ensure_properties(obj)

    obj.ExcitationFMax = 7.5e9
    obj.MaxSimulationTime = 250e-9
    obj.ExcitationType = "Sinusoid"

    proxy.ensure_properties(obj)

    assert obj.ExcitationFMax == 7.5e9
    assert obj.MaxSimulationTime == 250e-9
    assert obj.ExcitationType == "Sinusoid"
    assert list(obj._props).count("ExcitationFMax") == 1
    assert list(obj._props).count("MaxSimulationTime") == 1


def test_recompute_simulation_timestep_budget_updates_computed_values(monkeypatch):
    from OpenEMSWorkbench.objects import simulation_feature

    class _Proxy:
        def __init__(self, proxy_type: str):
            self.TYPE = proxy_type

    class _Mesh:
        coordinate_system = "Cartesian"
        x = (0.0, 1.0, 2.0)
        y = (0.0, 1.0, 2.0)
        z = (0.0, 1.0, 2.0)

    class _Analysis:
        def __init__(self):
            self.Proxy = _Proxy("OpenEMS_Analysis")
            self.Group = []

    class _Doc:
        def __init__(self, obj):
            self.Objects = [obj, _Analysis()]

    class _Obj:
        def __init__(self):
            self.MaxSimulationTime = 100e-9
            self.DeltaUnit = 1e-3
            self.ComputedTimeStep = 0.0
            self.ComputedTimeStepDisplay = ""
            self.ComputedNumberOfTimeSteps = 0
            self.ComputedNumberOfTimeStepsRaw = ""
            self.ComputedNumberOfTimeStepsScientific = ""
            self.ComputedLengthUnitName = ""
            self.NumberOfTimeSteps = 0
            self.TimeStepBudgetStatus = ""
            self.TimeStepBudgetLastReportKey = ""
            self.MaxSimulationTimeDisplay = ""

    obj = _Obj()
    doc = _Doc(obj)
    obj.Document = doc
    analysis = doc.Objects[1]
    analysis.Group = [obj]

    monkeypatch.setattr(simulation_feature, "build_mesh_for_analysis", lambda _analysis: (_analysis, None, _Mesh()))
    monkeypatch.setattr(simulation_feature, "detect_freecad_unit_contract", lambda: ("mm", 1e-3))

    ok, _message = simulation_feature.recompute_simulation_timestep_budget(obj)

    assert ok is True
    assert obj.ComputedTimeStep > 0.0
    assert obj.ComputedNumberOfTimeSteps >= 1
    assert obj.NumberOfTimeSteps == obj.ComputedNumberOfTimeSteps
    assert obj.ComputedLengthUnitName == "mm"
    assert "e" in obj.ComputedNumberOfTimeStepsScientific
    assert obj.MaxSimulationTimeDisplay.endswith(" sec")
    assert obj.ComputedTimeStepDisplay.endswith(" sec")


def test_recompute_simulation_timestep_budget_can_skip_report_updates(monkeypatch):
    from OpenEMSWorkbench.objects import simulation_feature

    class _Proxy:
        def __init__(self, proxy_type: str):
            self.TYPE = proxy_type

    class _Mesh:
        coordinate_system = "Cartesian"
        x = (0.0, 1.0, 2.0)
        y = (0.0, 1.0, 2.0)
        z = (0.0, 1.0, 2.0)

    class _Analysis:
        def __init__(self):
            self.Proxy = _Proxy("OpenEMS_Analysis")
            self.Group = []

    class _Doc:
        def __init__(self, obj):
            self.Objects = [obj, _Analysis()]

    class _Obj:
        def __init__(self):
            self.MaxSimulationTime = 100e-9
            self.DeltaUnit = 1e-3
            self.ComputedTimeStep = 0.0
            self.ComputedTimeStepDisplay = ""
            self.ComputedNumberOfTimeSteps = 0
            self.ComputedNumberOfTimeStepsRaw = ""
            self.ComputedNumberOfTimeStepsScientific = ""
            self.ComputedLengthUnitName = ""
            self.NumberOfTimeSteps = 0
            self.TimeStepBudgetStatus = ""
            self.TimeStepBudgetLastReportKey = "existing-key"
            self.MaxSimulationTimeDisplay = ""

    obj = _Obj()
    doc = _Doc(obj)
    obj.Document = doc
    analysis = doc.Objects[1]
    analysis.Group = [obj]

    monkeypatch.setattr(simulation_feature, "build_mesh_for_analysis", lambda _analysis: (_analysis, None, _Mesh()))
    monkeypatch.setattr(simulation_feature, "detect_freecad_unit_contract", lambda: ("mm", 1e-3))

    ok, _message = simulation_feature.recompute_simulation_timestep_budget(obj, emit_report=False)

    assert ok is True
    assert obj.TimeStepBudgetLastReportKey == "existing-key"
    assert obj.ComputedTimeStepDisplay.endswith(" sec")


def test_simulation_proxy_hides_internal_duplicate_properties_in_data_display():
    from OpenEMSWorkbench.objects.simulation_feature import OpenEMSSimulationProxy

    obj = FakeObject()
    proxy = OpenEMSSimulationProxy()
    proxy.ensure_properties(obj)

    assert obj._editor_modes.get("ComputedNumberOfTimeSteps") == 2
    assert obj._editor_modes.get("ComputedNumberOfTimeStepsRaw") == 2
    assert obj._editor_modes.get("ComputedNumberOfTimeStepsScientific") == 2
    assert obj._editor_modes.get("MaxSimulationTime") == 2
    assert obj._editor_modes.get("ComputedTimeStep") == 2
    assert obj._editor_modes.get("ComputedLengthUnitName") == 2
    assert obj._editor_modes.get("TimeStepBudgetStatus") == 2
    assert obj._editor_modes.get("TimeStepBudgetLastReportKey") == 2


def test_simulation_viewprovider_claims_simulation_box_helper_child():
    from OpenEMSWorkbench.objects.simulation_feature import OpenEMSSimulationViewProvider

    class _AnalysisProxy:
        TYPE = "OpenEMS_Analysis"

    simulation_obj = type("Simulation", (), {})()
    sim_box = type("SimBox", (), {"OpenEMSSimulationBox": True})()
    analysis_obj = type("Analysis", (), {"Proxy": _AnalysisProxy(), "Group": []})()
    analysis_obj.Group = [simulation_obj, sim_box]
    document = type("Doc", (), {"Objects": [analysis_obj]})()
    simulation_obj.Document = document

    viewprovider = OpenEMSSimulationViewProvider()
    viewprovider.attach(type("ViewObj", (), {"Object": simulation_obj})())

    assert viewprovider.claimChildren() == [sim_box]


def test_simulation_viewprovider_claims_legacy_simulation_box_by_name_fallback():
    from OpenEMSWorkbench.objects.simulation_feature import OpenEMSSimulationViewProvider

    class _AnalysisProxy:
        TYPE = "OpenEMS_Analysis"

    simulation_obj = type("Simulation", (), {})()
    legacy_box = type("LegacyBox", (), {"Name": "OpenEMSSimulationBox001", "Label": "openEMS Simulation Box"})()
    analysis_obj = type("Analysis", (), {"Proxy": _AnalysisProxy(), "Group": []})()
    analysis_obj.Group = [simulation_obj, legacy_box]
    document = type("Doc", (), {"Objects": [analysis_obj, legacy_box]})()
    simulation_obj.Document = document

    viewprovider = OpenEMSSimulationViewProvider()
    viewprovider.attach(type("ViewObj", (), {"Object": simulation_obj})())

    assert viewprovider.claimChildren() == [legacy_box]

