"""I/O package compatibility wrapper."""

try:
    from execution.process_runner import ProcessRunResult, run_process_blocking
except ImportError:
    from OpenEMSWorkbench.execution.process_runner import (
        ProcessRunResult,
        run_process_blocking,
    )


__all__ = ["ProcessRunResult", "run_process_blocking"]


