from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_workbench_command_registry_contains_phase2_commands():
    from OpenEMSWorkbench.commands import workbench_commands

    expected = {
        "OpenEMS_CreateAnalysis",
        "OpenEMS_CreateSimulation",
        "OpenEMS_CreateMaterial",
        "OpenEMS_CreatePort",
        "OpenEMS_CreateGrid",
        "OpenEMS_CreateDumpBox",
        "OpenEMS_SetActiveAnalysis",
        "OpenEMS_AssignSelectedToActiveAnalysis",
        "OpenEMS_EditSelected",
        "OpenEMS_RunPreflight",
        "OpenEMS_ExportDryRun",
        "OpenEMS_RunSimulation",
        "OpenEMS_ValidateRuntime",
        "OpenEMS_ConfigureRuntime",
        "OpenEMS_ShowHideMeshOverlay",
        "OpenEMS_RefreshMeshOverlay",
    }
    assert expected.issubset(set(workbench_commands.WORKBENCH_COMMANDS))


def test_grouped_workbench_layout_exports():
    from OpenEMSWorkbench.commands import workbench_commands

    assert workbench_commands.WORKBENCH_TOOLBAR
    assert workbench_commands.WORKBENCH_MENU
    assert all(isinstance(name, str) for name in workbench_commands.WORKBENCH_TOOLBAR)
    assert all(len(group) == 2 for group in workbench_commands.WORKBENCH_MENU)

    menu_sections = [name for name, _ in workbench_commands.WORKBENCH_MENU]
    assert menu_sections == ["Create", "Analysis", "Run", "Runtime", "View"]

    toolbar_commands = set(workbench_commands.WORKBENCH_TOOLBAR)
    assert "OpenEMS_CreateBoundary" not in toolbar_commands
    assert "OpenEMS_CreateDumpBox" not in toolbar_commands
    assert "OpenEMS_CreatePort" in toolbar_commands
    assert "OpenEMS_RunSimulation" in toolbar_commands


def test_flat_command_order_matches_group_layout():
    from OpenEMSWorkbench.commands import object_commands

    expected = []
    for _, group_commands in object_commands.WORKBENCH_MENU_GROUPS:
        expected.extend(group_commands)

    assert object_commands.WORKBENCH_OBJECT_COMMANDS == expected
    assert set(object_commands.WORKBENCH_TOOLBAR_COMMANDS).issubset(
        set(object_commands.WORKBENCH_OBJECT_COMMANDS)
    )


def test_object_command_definitions_exist():
    from OpenEMSWorkbench.commands.object_commands import COMMAND_DEFINITIONS, EDIT_COMMAND_NAME

    assert len(COMMAND_DEFINITIONS) == 6
    assert "OpenEMS_CreateAnalysis" in COMMAND_DEFINITIONS
    assert "OpenEMS_CreateSimulation" in COMMAND_DEFINITIONS
    assert "icon" in COMMAND_DEFINITIONS["OpenEMS_CreateSimulation"]
    assert EDIT_COMMAND_NAME == "OpenEMS_EditSelected"
