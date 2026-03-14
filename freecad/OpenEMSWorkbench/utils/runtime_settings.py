from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD runtime only
    App = None


_PARAM_ROOT = "User parameter:BaseApp/Preferences/Mod/OpenEMSWorkbench"
_PARAM_SOLVER_EXECUTABLE = "SolverExecutable"


def _param_group():
    if App is None or not hasattr(App, "ParamGet"):
        return None
    return App.ParamGet(_PARAM_ROOT)


def get_saved_solver_executable() -> str:
    group = _param_group()
    if group is None:
        return ""
    try:
        return str(group.GetString(_PARAM_SOLVER_EXECUTABLE, "") or "").strip()
    except Exception:
        return ""


def set_saved_solver_executable(executable: str) -> bool:
    group = _param_group()
    if group is None:
        return False
    try:
        group.SetString(_PARAM_SOLVER_EXECUTABLE, str(executable or "").strip())
        return True
    except Exception:
        return False


__all__ = ["get_saved_solver_executable", "set_saved_solver_executable"]
