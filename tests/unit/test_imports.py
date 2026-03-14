from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_package_metadata_imports():
    from OpenEMSWorkbench import metadata, version

    assert metadata.WORKBENCH_NAME == "OpenEMS"
    assert version.__version__ == "0.1.0"


def test_paths_module_resolves_resource_root():
    from OpenEMSWorkbench.utils.paths import package_root, resources_dir

    assert package_root().name == "OpenEMSWorkbench"
    assert resources_dir().name == "resources"


def test_command_module_imports_without_freecad():
    from OpenEMSWorkbench.commands import workbench_commands

    assert "OpenEMS_CreateSimulation" in workbench_commands.WORKBENCH_COMMANDS
    assert "OpenEMS_EditSelected" in workbench_commands.WORKBENCH_COMMANDS
