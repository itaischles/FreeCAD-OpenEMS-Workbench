from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_run_process_blocking_captures_stdout_and_stderr(tmp_path):
    from OpenEMSWorkbench.io import run_process_blocking

    stdout_log = tmp_path / "logs" / "stdout.log"
    stderr_log = tmp_path / "logs" / "stderr.log"
    result = run_process_blocking(
        command=[
            sys.executable,
            "-c",
            "import sys; print('hello from test'); print('error line', file=sys.stderr)",
        ],
        cwd=tmp_path,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
    )

    assert result.exit_code == 0
    assert stdout_log.exists()
    assert stderr_log.exists()
    assert "hello from test" in stdout_log.read_text(encoding="utf-8")
    assert "error line" in stderr_log.read_text(encoding="utf-8")


def test_run_process_blocking_streams_callbacks(tmp_path):
    from OpenEMSWorkbench.io import run_process_blocking

    seen_stdout: list[str] = []
    seen_stderr: list[str] = []

    stdout_log = tmp_path / "logs" / "stdout.log"
    stderr_log = tmp_path / "logs" / "stderr.log"
    result = run_process_blocking(
        command=[
            sys.executable,
            "-c",
            (
                "import sys; "
                "print('line one'); "
                "print('line two'); "
                "print('warn one', file=sys.stderr)"
            ),
        ],
        cwd=tmp_path,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        on_stdout_line=seen_stdout.append,
        on_stderr_line=seen_stderr.append,
    )

    assert result.exit_code == 0
    assert any("line one" in line for line in seen_stdout)
    assert any("line two" in line for line in seen_stdout)
    assert any("warn one" in line for line in seen_stderr)
