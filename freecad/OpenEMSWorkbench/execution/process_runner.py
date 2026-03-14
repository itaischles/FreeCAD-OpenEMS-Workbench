from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import threading
import time


@dataclass
class ProcessRunResult:
    exit_code: int
    command: list[str]
    cwd: str
    duration_seconds: float
    stdout_log: str
    stderr_log: str


def _normalize_exit_code(code: int) -> int:
    # Windows may surface negative process exits as unsigned 32-bit values.
    if code > 0x7FFFFFFF:
        return code - 0x100000000
    return code


def run_process_blocking(
    command: list[str],
    cwd: str | Path,
    stdout_log: str | Path,
    stderr_log: str | Path,
    env: dict[str, str] | None = None,
    on_stdout_line=None,
    on_stderr_line=None,
) -> ProcessRunResult:
    if not command:
        raise ValueError("Execution command cannot be empty.")

    cwd_path = Path(cwd)
    cwd_path.mkdir(parents=True, exist_ok=True)

    stdout_path = Path(stdout_log)
    stderr_path = Path(stderr_log)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)

    popen_kwargs = {
        "cwd": str(cwd_path),
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "bufsize": 1,
    }
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    process = subprocess.Popen(command, **popen_kwargs)

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def _consume(pipe, collector: list[str], callback):
        if pipe is None:
            return
        for line in iter(pipe.readline, ""):
            collector.append(line)
            if callback is not None:
                try:
                    callback(line.rstrip("\r\n"))
                except Exception:
                    pass
        pipe.close()

    started = time.perf_counter()
    stdout_thread = threading.Thread(
        target=_consume,
        args=(process.stdout, stdout_lines, on_stdout_line),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_consume,
        args=(process.stderr, stderr_lines, on_stderr_line),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    exit_code = process.wait()
    stdout_thread.join()
    stderr_thread.join()
    duration = time.perf_counter() - started

    stdout_path.write_text("".join(stdout_lines), encoding="utf-8")
    stderr_path.write_text("".join(stderr_lines), encoding="utf-8")

    return ProcessRunResult(
        exit_code=_normalize_exit_code(int(exit_code)),
        command=list(command),
        cwd=str(cwd_path),
        duration_seconds=duration,
        stdout_log=str(stdout_path),
        stderr_log=str(stderr_path),
    )


__all__ = ["ProcessRunResult", "run_process_blocking"]
