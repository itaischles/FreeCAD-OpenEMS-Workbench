from __future__ import annotations

try:
    import FreeCADGui as Gui
except ImportError:  # pragma: no cover - exercised only inside FreeCAD
    Gui = None

try:
    from commands.object_commands import WORKBENCH_OBJECT_COMMANDS, register_object_commands
except ImportError:
    from OpenEMSWorkbench.commands.object_commands import (
        WORKBENCH_OBJECT_COMMANDS,
        register_object_commands,
    )


WORKBENCH_COMMANDS = WORKBENCH_OBJECT_COMMANDS


def register_commands():
    if Gui is None:
        return []
    return register_object_commands()
