from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


_CHECK_SNIPPET = "\n".join(
    [
        "import json",
        "import os",
        "import tempfile",
        "root = (os.environ.get('OPENEMS_INSTALL_DIR', '') or os.environ.get('OPENEMS_INSTALL_PATH', '')).strip()",
        "if root and hasattr(os, 'add_dll_directory'):",
        "    os.add_dll_directory(root)",
        "import openEMS",
        "import CSXCAD",
        "from CSXCAD import CSPrimitives as _csprims",
        "reader_cls = getattr(_csprims, 'CSPrimPolyhedronReader', None)",
        "stl_enum = getattr(_csprims, 'STL_FILE', None)",
        "stl_smoke_ok = False",
        "stl_smoke_error = ''",
        "_probe_path = ''",
        "try:",
        "    csx = CSXCAD.ContinuousStructure()",
        "    pec = csx.AddMetal('runtime_probe')",
        "    fd, _probe_path = tempfile.mkstemp(suffix='.stl')",
        "    os.close(fd)",
        "    with open(_probe_path, 'w', encoding='ascii') as _fh:",
        "        _fh.write('solid runtime_probe\\n facet normal 0 0 1\\n  outer loop\\n   vertex 0 0 0\\n   vertex 1 0 0\\n   vertex 0 1 0\\n  endloop\\n endfacet\\nendsolid runtime_probe\\n')",
        "    _reader = pec.AddPolyhedronReader(_probe_path, priority=1)",
        "    _probe_result = _reader.ReadFile()",
        "    stl_smoke_ok = (_probe_result is not False)",
        "except Exception as _exc:",
        "    stl_smoke_error = type(_exc).__name__ + ': ' + str(_exc)",
        "finally:",
        "    if _probe_path and os.path.isfile(_probe_path):",
        "        os.remove(_probe_path)",
        "payload = {'capabilities': {'stl_reader': bool(reader_cls is not None and (stl_enum is not None or stl_smoke_ok))},",
        "           'details': {'polyhedron_reader_class': 'present' if reader_cls is not None else 'missing',",
        "                      'stl_file_enum': 'present' if stl_enum is not None else 'missing',",
        "                      'stl_smoke_test': 'passed' if stl_smoke_ok else 'failed',",
        "                      'stl_smoke_error': stl_smoke_error}}",
        "print('OPENEMS_PYTHON_RUNTIME=' + json.dumps(payload, sort_keys=True))",
    ]
)

_CHECK_PREFIX = "OPENEMS_PYTHON_RUNTIME="


@dataclass
class RuntimeDiscoveryResult:
    ok: bool
    executable: str = ""
    message: str = ""
    checked: list[str] = field(default_factory=list)
    capabilities: dict[str, bool] = field(default_factory=dict)
    details: dict[str, str] = field(default_factory=dict)


def _normalize_candidate(path: str) -> str:
    text = str(path).strip().strip('"')
    return os.path.normpath(text) if text else ""


def _resolve_openems_install_dir() -> str:
    env_root = _normalize_candidate(os.environ.get("OPENEMS_INSTALL_DIR", ""))
    if env_root and os.path.isdir(env_root):
        return env_root

    try:
        try:
            from utils.runtime_settings import get_saved_openems_install_dir
        except ImportError:
            from OpenEMSWorkbench.utils.runtime_settings import get_saved_openems_install_dir
        saved_root = _normalize_candidate(get_saved_openems_install_dir())
        if saved_root and os.path.isdir(saved_root):
            return saved_root
    except Exception:
        pass

    fallback = _normalize_candidate(r"C:\openEMS")
    if fallback and os.path.isdir(fallback):
        return fallback
    return ""


def _probe_python_runtime(executable: str, timeout_seconds: int = 20) -> tuple[bool, str]:
    result = inspect_python_runtime(executable, timeout_seconds=timeout_seconds)
    return result.ok, result.message or "ok"


def _format_capability_suffix(capabilities: dict[str, bool]) -> str:
    stl_reader = bool(capabilities.get("stl_reader", False))
    status = "available" if stl_reader else "unavailable"
    return f"STL reader: {status}"


def inspect_python_runtime(executable: str, timeout_seconds: int = 20) -> RuntimeDiscoveryResult:
    candidate = _normalize_candidate(executable)
    if not candidate:
        return RuntimeDiscoveryResult(ok=False, executable="", message="empty candidate")

    env = dict(os.environ)
    openems_root = _resolve_openems_install_dir()
    if openems_root:
        env["OPENEMS_INSTALL_DIR"] = openems_root
        env["OPENEMS_INSTALL_PATH"] = openems_root
        env["PATH"] = openems_root + os.pathsep + env.get("PATH", "")

    try:
        proc = subprocess.run(
            [candidate, "-c", _CHECK_SNIPPET],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return RuntimeDiscoveryResult(
            ok=False,
            executable=candidate,
            message=f"timeout after {timeout_seconds}s",
        )
    except Exception as exc:
        return RuntimeDiscoveryResult(ok=False, executable=candidate, message=str(exc))

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    payload_line = ""
    for line in reversed(stdout.splitlines()):
        text = line.strip()
        if text.startswith(_CHECK_PREFIX):
            payload_line = text
            break

    if proc.returncode == 0 and payload_line:
        try:
            payload = json.loads(payload_line[len(_CHECK_PREFIX) :])
        except json.JSONDecodeError as exc:
            return RuntimeDiscoveryResult(
                ok=False,
                executable=candidate,
                message=f"invalid runtime probe output: {exc}",
            )

        capabilities = {
            str(key): bool(value)
            for key, value in dict(payload.get("capabilities", {}) or {}).items()
        }
        details = {
            str(key): str(value)
            for key, value in dict(payload.get("details", {}) or {}).items()
        }
        return RuntimeDiscoveryResult(
            ok=True,
            executable=candidate,
            message=_format_capability_suffix(capabilities),
            capabilities=capabilities,
            details=details,
        )

    detail = stderr or stdout or f"exit={proc.returncode}"
    return RuntimeDiscoveryResult(ok=False, executable=candidate, message=detail)


def _candidate_executables(preferred_candidates: list[str] | None = None) -> list[str]:
    candidates: list[str] = []

    for candidate in list(preferred_candidates or []):
        candidates.append(candidate)

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


def discover_python_runtime(preferred_candidates: list[str] | None = None) -> RuntimeDiscoveryResult:
    checked: list[str] = []
    candidates = (
        _candidate_executables(preferred_candidates)
        if preferred_candidates is not None
        else _candidate_executables()
    )
    for candidate in candidates:
        result = inspect_python_runtime(candidate)
        detail = result.message
        checked.append(f"{candidate}: {detail}")
        if result.ok:
            return RuntimeDiscoveryResult(
                ok=True,
                executable=candidate,
                message=(
                    f"Detected Python runtime with openEMS modules: {candidate} "
                    f"({_format_capability_suffix(result.capabilities)})"
                ),
                checked=checked,
                capabilities=result.capabilities,
                details=result.details,
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
    result = inspect_python_runtime(candidate)
    if result.ok:
        return True, (
            f"Python runtime check passed: {candidate} "
            f"({_format_capability_suffix(result.capabilities)})"
        )
    return False, f"Python runtime check failed for '{candidate}': {result.message}"


__all__ = [
    "RuntimeDiscoveryResult",
    "discover_python_runtime",
    "inspect_python_runtime",
    "validate_python_runtime",
]
