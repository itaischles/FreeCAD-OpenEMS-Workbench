from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
FREECAD_PACKAGE_ROOT = REPO_ROOT / "freecad"

if str(FREECAD_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(FREECAD_PACKAGE_ROOT))


def test_waveguide_summary_text_reports_supported_detection_and_inference():
    from OpenEMSWorkbench.gui.task_panels.port_panel import _waveguide_summary_text

    detection = {
        "status": "supported",
        "kind": "coax_axis_aligned",
        "selected_face": "ZMin",
        "axis": "z",
        "inner": {"geometry_name": "InnerPin", "radius": 1.0},
        "outer": {"geometry_name": "OuterShield", "radius": 2.0},
    }
    inference = {
        "status": "supported",
        "r_in": 1.0,
        "r_out": 2.0,
        "dielectric_epsilon_r": 2.2,
    }

    text = _waveguide_summary_text(detection, inference)
    assert "Geometry detection: supported" in text
    assert "Inner conductor: InnerPin" in text
    assert "Inferred coax: r_in=1.0, r_out=2.0, epsilon_r=2.2" in text


def test_waveguide_summary_text_reports_unsupported_detection_reason():
    from OpenEMSWorkbench.gui.task_panels.port_panel import _waveguide_summary_text

    detection = {
        "status": "unsupported",
        "reason": "insufficient_cylinder_candidates",
        "inspected": [
            {
                "geometry_name": "OuterTube",
                "touched_selected_face": True,
                "inferred_axis": "z",
                "inferred_radius": 2.1,
                "support_reason": "tube_properties",
                "rejection_reason": None,
                "radius_from_properties": {"radius": 2.0, "inner_radius": 1.6, "source": "tube_properties"},
                "bounds": {"xmin": 2.8, "xmax": 7.2, "ymin": 2.8, "ymax": 7.2, "zmin": 0.0, "zmax": 8.0},
            }
        ],
    }
    inference = {
        "status": "unsupported",
        "reason": "geometry_detection_not_supported",
    }

    text = _waveguide_summary_text(detection, inference)
    assert "unsupported (insufficient_cylinder_candidates)" in text
    assert "Inspected solids:" in text
    assert "OuterTube" in text
    assert "radius_props={'radius': 2.0, 'inner_radius': 1.6, 'source': 'tube_properties'}" in text


def test_waveguide_report_line_reports_unsupported_detection_note():
    from OpenEMSWorkbench.gui.task_panels.port_panel import _waveguide_report_line

    detection = {
        "status": "unsupported",
        "selected_face": "ZMin",
        "reason": "insufficient_cylinder_candidates",
    }

    report_line = _waveguide_report_line(detection, None)
    assert report_line == "No supported coax geometry detected on ZMin (insufficient_cylinder_candidates)."
