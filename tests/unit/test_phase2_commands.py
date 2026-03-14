from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_workbench_command_registry_contains_phase2_commands():
    from OpenEMSWorkbench.commands import workbench_commands

    expected = {
        "OpenEMS_CreateSimulation",
        "OpenEMS_CreateMaterial",
        "OpenEMS_CreateBoundary",
        "OpenEMS_CreatePort",
        "OpenEMS_CreateGrid",
        "OpenEMS_CreateDumpBox",
        "OpenEMS_Placeholder",
    }
    assert expected.issubset(set(workbench_commands.WORKBENCH_COMMANDS))


def test_object_command_definitions_exist():
    from OpenEMSWorkbench.commands.object_commands import COMMAND_DEFINITIONS

    assert len(COMMAND_DEFINITIONS) == 6
    assert "OpenEMS_CreateSimulation" in COMMAND_DEFINITIONS
