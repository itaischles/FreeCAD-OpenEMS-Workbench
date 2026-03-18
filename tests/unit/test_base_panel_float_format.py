from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_parse_float_text_accepts_scientific_notation():
    from OpenEMSWorkbench.gui.task_panels.base_panel import parse_float_text

    assert parse_float_text("1e6") == 1_000_000.0
    assert parse_float_text("2.5e-9") == 2.5e-9


def test_parse_float_text_uses_fallback_on_invalid_input():
    from OpenEMSWorkbench.gui.task_panels.base_panel import parse_float_text

    assert parse_float_text("not-a-number", fallback=3.14) == 3.14


def test_format_float_text_prefers_scientific_for_large_and_small_values():
    from OpenEMSWorkbench.gui.task_panels.base_panel import format_float_text

    assert format_float_text(1_000_000.0) == "1e6"
    assert format_float_text(2.5e-9) == "2.5e-9"


def test_format_float_text_keeps_plain_decimal_for_midrange_values():
    from OpenEMSWorkbench.gui.task_panels.base_panel import format_float_text

    assert format_float_text(123.5) == "123.5"
    assert format_float_text(0.25) == "0.25"
