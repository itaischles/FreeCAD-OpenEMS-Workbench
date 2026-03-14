from __future__ import annotations

try:
    import FreeCAD as App
except ImportError:  # pragma: no cover - FreeCAD runtime only
    App = None

try:
    from utils.analysis_context import add_member_to_analysis, get_active_analysis, set_active_analysis, get_analyses
except ImportError:
    from OpenEMSWorkbench.utils.analysis_context import (
        add_member_to_analysis,
        get_active_analysis,
        get_analyses,
        set_active_analysis,
    )

try:
    from objects.analysis_feature import OpenEMSAnalysisProxy, OpenEMSAnalysisViewProvider
    from objects.boundary_feature import OpenEMSBoundaryProxy, OpenEMSBoundaryViewProvider
    from objects.dumpbox_feature import OpenEMSDumpBoxProxy, OpenEMSDumpBoxViewProvider
    from objects.grid_feature import OpenEMSGridProxy, OpenEMSGridViewProvider
    from objects.material_feature import OpenEMSMaterialProxy, OpenEMSMaterialViewProvider
    from objects.port_feature import OpenEMSPortProxy, OpenEMSPortViewProvider
    from objects.simulation_feature import (
        OpenEMSSimulationProxy,
        OpenEMSSimulationViewProvider,
    )
except ImportError:
    from OpenEMSWorkbench.objects.analysis_feature import (
        OpenEMSAnalysisProxy,
        OpenEMSAnalysisViewProvider,
    )
    from OpenEMSWorkbench.objects.boundary_feature import (
        OpenEMSBoundaryProxy,
        OpenEMSBoundaryViewProvider,
    )
    from OpenEMSWorkbench.objects.dumpbox_feature import (
        OpenEMSDumpBoxProxy,
        OpenEMSDumpBoxViewProvider,
    )
    from OpenEMSWorkbench.objects.grid_feature import OpenEMSGridProxy, OpenEMSGridViewProvider
    from OpenEMSWorkbench.objects.material_feature import (
        OpenEMSMaterialProxy,
        OpenEMSMaterialViewProvider,
    )
    from OpenEMSWorkbench.objects.port_feature import OpenEMSPortProxy, OpenEMSPortViewProvider
    from OpenEMSWorkbench.objects.simulation_feature import (
        OpenEMSSimulationProxy,
        OpenEMSSimulationViewProvider,
    )


def _create_feature(
    doc,
    object_type: str,
    internal_name: str,
    label: str,
    proxy_cls,
    viewprovider_cls,
    auto_attach_to_active: bool = True,
):
    obj = doc.addObject(object_type, internal_name)
    proxy_cls().attach(obj)
    if App is not None and getattr(App, "GuiUp", False):
        viewprovider_cls().attach(obj.ViewObject)
    obj.Label = label

    if auto_attach_to_active:
        analysis = get_active_analysis(doc)
        add_member_to_analysis(analysis, obj)

    doc.recompute()
    return obj


def create_analysis(doc):
    existing_analyses = get_analyses(doc)
    analysis = _create_feature(
        doc,
        "App::DocumentObjectGroupPython",
        "OpenEMSAnalysis",
        "openEMS Analysis",
        OpenEMSAnalysisProxy,
        OpenEMSAnalysisViewProvider,
        auto_attach_to_active=False,
    )
    if not existing_analyses:
        set_active_analysis(doc, analysis)
    return analysis


def create_simulation(doc):
    return _create_feature(
        doc,
        "App::FeaturePython",
        "OpenEMSSimulation",
        "openEMS Simulation",
        OpenEMSSimulationProxy,
        OpenEMSSimulationViewProvider,
    )


def create_material(doc):
    return _create_feature(
        doc,
        "App::FeaturePython",
        "OpenEMSMaterial",
        "openEMS Material",
        OpenEMSMaterialProxy,
        OpenEMSMaterialViewProvider,
    )


def create_boundary(doc):
    return _create_feature(
        doc,
        "App::FeaturePython",
        "OpenEMSBoundary",
        "openEMS Boundary",
        OpenEMSBoundaryProxy,
        OpenEMSBoundaryViewProvider,
    )


def create_port(doc):
    return _create_feature(
        doc,
        "App::FeaturePython",
        "OpenEMSPort",
        "openEMS Port",
        OpenEMSPortProxy,
        OpenEMSPortViewProvider,
    )


def create_grid(doc):
    return _create_feature(
        doc,
        "App::FeaturePython",
        "OpenEMSGrid",
        "openEMS Grid",
        OpenEMSGridProxy,
        OpenEMSGridViewProvider,
    )


def create_dumpbox(doc):
    return _create_feature(
        doc,
        "App::FeaturePython",
        "OpenEMSDumpBox",
        "openEMS DumpBox",
        OpenEMSDumpBoxProxy,
        OpenEMSDumpBoxViewProvider,
    )
