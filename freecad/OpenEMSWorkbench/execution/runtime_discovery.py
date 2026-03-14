from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import subprocess
import sys


_CHECK_SNIPPET = (
    "import os; "
    "root=os.environ.get('OPENEMS_INSTALL_DIR','').strip(); "
    "(os.add_dll_directory(root) if (root and hasattr(os,'add_dll_directory')) else None); "
    "import openEMS, CSXCAD; "
    "print('OPENEMS_PYTHON_RUNTIME_OK')"
)


@dataclass
class RuntimeDiscoveryResult:
    ok: bool
    executable: str = ""
    message: str = ""
    checked: list[str] = field(default_factory=list)


def _normalize_candidate(path: str) -> str:
    text = str(path).strip().strip('"')
    return os.path.normpath(text) if text else ""


def _probe_python_runtime(executable: str, timeout_seconds: int = 8) -> tuple[bool, str]:
    candidate = _normalize_candidate(executable)
    if not candidate:
        return False, "empty candidate"

    try:
        proc = subprocess.run(
            [candidate, "-c", _CHECK_SNIPPET],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:
        return False, str(exc)

    if proc.returncode == 0 and "OPENEMS_PYTHON_RUNTIME_OK" in (proc.stdout or ""):
        return True, "ok"

    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    detail = stderr or stdout or f"exit={proc.returncode}"
    return False, detail


def _candidate_executables() -> list[str]:
    candidates: list[str] = []

    candidates.append(sys.executable)

    for name in ["python", "python3", "python.exe"]:
        resolved = shutil.which(name)
        if resolved:
            candidates.append(resolved)

    for env_name in ["OPENEMS_PYTHON", "PYTHON_EXECUTABLE"]:
        value = os.environ.get(env_name, "").strip()
        if value:
            candidates.append(value)

    # Keep order but remove duplicates after normalization.
    seen: set[str] = set()
    normalized: list[str] = []
    for candidate in candidates:
        text = _normalize_candidate(candidate)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return normalized


def discover_python_runtime() -> RuntimeDiscoveryResult:
    checked: list[str] = []
    for candidate in _candidate_executables():
        ok, detail = _probe_python_runtime(candidate)
        checked.append(f"{candidate}: {detail}")
        if ok:
            return RuntimeDiscoveryResult(
                ok=True,
                executable=candidate,
                message=f"Detected Python runtime with openEMS modules: {candidate}",
                checked=checked,
            )

    return RuntimeDiscoveryResult(
        ok=False,
        executable="",
        message="No Python runtime with openEMS/CSXCAD modules was detected automatically.",
        checked=checked,
    )


def validate_python_runtime(executable: str) -> tuple[bool, str]:
    candidate = _normalize_candidate(executable)
    if not candidate:
        return False, "SolverExecutable is empty."
    ok, detail = _probe_python_runtime(candidate)
    if ok:
        return True, f"Python runtime check passed: {candidate}"
    return False, f"Python runtime check failed for '{candidate}': {detail}"


__all__ = ["RuntimeDiscoveryResult", "discover_python_runtime", "validate_python_runtime"]
