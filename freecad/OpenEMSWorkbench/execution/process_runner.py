from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import time


@dataclass
class ProcessRunResult:
    exit_code: int
    command: list[str]
    cwd: str
    duration_seconds: float
    stdout_log: str
    stderr_log: str


def run_process_blocking(
    command: list[str],
    cwd: str | Path,
    stdout_log: str | Path,
    stderr_log: str | Path,
    env: dict[str, str] | None = None,
) -> ProcessRunResult:
    if not command:
        raise ValueError("Execution command cannot be empty.")

    cwd_path = Path(cwd)
    cwd_path.mkdir(parents=True, exist_ok=True)

    stdout_path = Path(stdout_log)
    stderr_path = Path(stderr_log)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=str(cwd_path),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    duration = time.perf_counter() - started

    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")

    return ProcessRunResult(
        exit_code=int(completed.returncode),
        command=list(command),
        cwd=str(cwd_path),
        duration_seconds=duration,
        stdout_log=str(stdout_path),
        stderr_log=str(stderr_path),
    )


__all__ = ["ProcessRunResult", "run_process_blocking"]
