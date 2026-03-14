from __future__ import annotations

try:
    import FreeCAD as App
except ImportError:  # pragma: no cover - FreeCAD runtime only
    App = None

try:
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


def _create_feature(doc, internal_name: str, label: str, proxy_cls, viewprovider_cls):
    obj = doc.addObject("App::FeaturePython", internal_name)
    proxy_cls().attach(obj)
    if App is not None and getattr(App, "GuiUp", False):
        viewprovider_cls().attach(obj.ViewObject)
    obj.Label = label
    doc.recompute()
    return obj


def create_simulation(doc):
    return _create_feature(
        doc,
        "OpenEMSSimulation",
        "openEMS Simulation",
        OpenEMSSimulationProxy,
        OpenEMSSimulationViewProvider,
    )


def create_material(doc):
    return _create_feature(
        doc,
        "OpenEMSMaterial",
        "openEMS Material",
        OpenEMSMaterialProxy,
        OpenEMSMaterialViewProvider,
    )


def create_boundary(doc):
    return _create_feature(
        doc,
        "OpenEMSBoundary",
        "openEMS Boundary",
        OpenEMSBoundaryProxy,
        OpenEMSBoundaryViewProvider,
    )


def create_port(doc):
    return _create_feature(
        doc,
        "OpenEMSPort",
        "openEMS Port",
        OpenEMSPortProxy,
        OpenEMSPortViewProvider,
    )


def create_grid(doc):
    return _create_feature(
        doc,
        "OpenEMSGrid",
        "openEMS Grid",
        OpenEMSGridProxy,
        OpenEMSGridViewProvider,
    )


def create_dumpbox(doc):
    return _create_feature(
        doc,
        "OpenEMSDumpBox",
        "openEMS DumpBox",
        OpenEMSDumpBoxProxy,
        OpenEMSDumpBoxViewProvider,
    )
