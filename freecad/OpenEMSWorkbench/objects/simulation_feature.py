from __future__ import annotations

try:
    from model import COORDINATE_SYSTEMS, DEFAULTS
    from objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )
except ImportError:
    from OpenEMSWorkbench.model import COORDINATE_SYSTEMS, DEFAULTS
    from OpenEMSWorkbench.objects.base_feature import (
        FeatureProxyBase,
        ViewProviderBase,
        add_property_if_missing,
        set_enum_choices,
    )


class OpenEMSSimulationProxy(FeatureProxyBase):
    TYPE = "OpenEMS_Simulation"

    def ensure_properties(self, obj):
        add_property_if_missing(
            obj,
            "App::PropertyString",
            "SolverName",
            "OpenEMS",
            "Target solver backend.",
            "openEMS",
        )
        add_property_if_missing(
            obj,
            "App::PropertyEnumeration",
            "CoordinateSystem",
            "OpenEMS",
            "Simulation coordinate system.",
            DEFAULTS["simulation"]["coordinate_system"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "DeltaUnit",
            "OpenEMS",
            "Length unit in meters.",
            DEFAULTS["simulation"]["delta_unit"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyInteger",
            "NumberOfTimeSteps",
            "OpenEMS",
            "Maximum number of FDTD timesteps.",
            DEFAULTS["simulation"]["nr_ts"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyFloat",
            "EndCriteria",
            "OpenEMS",
            "Stopping criteria for field energy decay.",
            DEFAULTS["simulation"]["end_criteria"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyString",
            "OutputDirectory",
            "OpenEMS",
            "Simulation output directory.",
            "",
        )
        add_property_if_missing(
            obj,
            "App::PropertyString",
            "SolverExecutable",
            "Run",
            "Executable used to run generated openEMS script.",
            DEFAULTS["simulation"]["solver_executable"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyString",
            "SolverArguments",
            "Run",
            "Optional arguments passed to the solver executable.",
            DEFAULTS["simulation"]["solver_arguments"],
        )
        add_property_if_missing(
            obj,
            "App::PropertyBool",
            "RunBlocking",
            "Run",
            "Run solver synchronously in FreeCAD UI thread.",
            DEFAULTS["simulation"]["run_blocking"],
        )
        set_enum_choices(
            obj,
            "CoordinateSystem",
            COORDINATE_SYSTEMS,
            DEFAULTS["simulation"]["coordinate_system"],
        )


class OpenEMSSimulationViewProvider(ViewProviderBase):
    TYPE = "OpenEMS_SimulationView"
