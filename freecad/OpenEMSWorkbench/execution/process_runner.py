from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
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

    callback_queue: Queue[tuple] = Queue()

    def _consume(pipe, collector: list[str], callback, stream):
        if pipe is None:
            return
        for line in iter(pipe.readline, ""):
            collector.append(line)
            stream.write(line)
            stream.flush()
            if callback is not None:
                callback_queue.put((callback, line.rstrip("\r\n")))
        pipe.close()

    started = time.perf_counter()
    with stdout_path.open("w", encoding="utf-8") as stdout_stream, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_stream:
        stdout_thread = threading.Thread(
            target=_consume,
            args=(process.stdout, stdout_lines, on_stdout_line, stdout_stream),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_consume,
            args=(process.stderr, stderr_lines, on_stderr_line, stderr_stream),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        while True:
            try:
                callback, payload = callback_queue.get(timeout=0.02)
                try:
                    callback(payload)
                except Exception:
                    pass
            except Empty:
                pass

            if (
                process.poll() is not None
                and not stdout_thread.is_alive()
                and not stderr_thread.is_alive()
                and callback_queue.empty()
            ):
                break

        exit_code = process.wait()
        stdout_thread.join()
        stderr_thread.join()

    duration = time.perf_counter() - started

    return ProcessRunResult(
        exit_code=_normalize_exit_code(int(exit_code)),
        command=list(command),
        cwd=str(cwd_path),
        duration_seconds=duration,
        stdout_log=str(stdout_path),
        stderr_log=str(stderr_path),
    )


__all__ = ["ProcessRunResult", "run_process_blocking"]
