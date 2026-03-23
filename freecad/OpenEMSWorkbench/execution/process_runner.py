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
    timed_out: bool = False


@dataclass
class ProcessLaunchResult:
    pid: int
    command: list[str]
    cwd: str
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
    timeout_seconds: float = 0.0,
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
    timed_out = False

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

            if timeout_seconds > 0.0 and (time.perf_counter() - started) >= float(timeout_seconds):
                timed_out = True
                try:
                    process.terminate()
                except Exception:
                    pass
                try:
                    process.wait(timeout=2.0)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
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
        timed_out=timed_out,
    )


def run_process_in_terminal(
    command: list[str],
    cwd: str | Path,
    stdout_log: str | Path,
    stderr_log: str | Path,
    env: dict[str, str] | None = None,
    title: str = "openEMS Simulation",
) -> ProcessLaunchResult:
    if not command:
        raise ValueError("Execution command cannot be empty.")

    cwd_path = Path(cwd)
    cwd_path.mkdir(parents=True, exist_ok=True)

    stdout_path = Path(stdout_log)
    stderr_path = Path(stderr_log)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)

    command_line = subprocess.list2cmdline([str(part) for part in command])
    stdout_quoted = str(stdout_path).replace('"', '""')
    stderr_quoted = str(stderr_path).replace('"', '""')
    inner_script = (
        f"echo openEMS run launched. && "
        f"echo Logging stdout to: {stdout_quoted} && "
        f"echo Logging stderr to: {stderr_quoted} && "
        f"{command_line} 1>>\"{stdout_quoted}\" 2>>\"{stderr_quoted}\" && "
        "echo. && "
        "echo Process exited with code %ERRORLEVEL%. && "
        "pause"
    )

    if hasattr(subprocess, "CREATE_NEW_CONSOLE"):
        launcher = subprocess.Popen(
            ["cmd.exe", "/c", "start", title, "cmd.exe", "/k", inner_script],
            cwd=str(cwd_path),
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        launcher = subprocess.Popen(
            ["x-terminal-emulator", "-e", command_line],
            cwd=str(cwd_path),
            env=env,
        )

    return ProcessLaunchResult(
        pid=int(getattr(launcher, "pid", 0) or 0),
        command=list(command),
        cwd=str(cwd_path),
        stdout_log=str(stdout_path),
        stderr_log=str(stderr_path),
    )


__all__ = [
    "ProcessRunResult",
    "ProcessLaunchResult",
    "run_process_blocking",
    "run_process_in_terminal",
]
