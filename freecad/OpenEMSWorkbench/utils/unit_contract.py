from __future__ import annotations

try:
    import FreeCAD as App
except Exception:  # pragma: no cover - FreeCAD runtime only
    App = None


DEFAULT_LENGTH_UNIT_NAME = "mm"
DEFAULT_DELTA_UNIT_METERS = 1e-3
_DELTA_UNIT_TOLERANCE = 1e-12


def canonical_delta_unit_meters() -> float:
    return float(DEFAULT_DELTA_UNIT_METERS)


def detect_freecad_unit_contract() -> tuple[str, float]:
    if App is None or not hasattr(App, "Units"):
        return DEFAULT_LENGTH_UNIT_NAME, canonical_delta_unit_meters()

    try:
        quantity = App.Units.Quantity("1 mm")
        preferred = quantity.getUserPreferred()
        if isinstance(preferred, (list, tuple)) and len(preferred) >= 2:
            preferred_value = float(preferred[0])
            preferred_unit = str(preferred[1] or "").strip() or DEFAULT_LENGTH_UNIT_NAME
            if preferred_value > 0.0:
                # 1 mm = 1e-3 m; preferred_value is how many user units fit in 1 mm.
                delta_unit = 1e-3 / preferred_value
                return preferred_unit, float(delta_unit)
    except Exception:
        pass

    return DEFAULT_LENGTH_UNIT_NAME, canonical_delta_unit_meters()


def detect_freecad_length_unit_name() -> str:
    name, _ = detect_freecad_unit_contract()
    return name


def detect_freecad_delta_unit_meters() -> float:
    _, delta = detect_freecad_unit_contract()
    return float(delta)


def is_supported_delta_unit(value, expected_delta_unit: float | None = None) -> bool:
    expected = (
        float(expected_delta_unit)
        if expected_delta_unit is not None
        else canonical_delta_unit_meters()
    )
    try:
        numeric = float(value)
    except Exception:
        return False
    return abs(numeric - expected) <= _DELTA_UNIT_TOLERANCE


def coerce_delta_unit(value, fallback_delta_unit: float | None = None) -> float:
    expected = (
        float(fallback_delta_unit)
        if fallback_delta_unit is not None
        else canonical_delta_unit_meters()
    )
    if is_supported_delta_unit(value, expected_delta_unit=expected):
        return float(value)
    return expected


def mm_to_model_unit_scale(delta_unit_meters: float) -> float:
    delta = float(delta_unit_meters)
    if delta <= 0.0:
        return 1.0
    return 1e-3 / delta
