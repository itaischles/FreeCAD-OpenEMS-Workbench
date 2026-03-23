from __future__ import annotations

import math


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _is_pec(material: dict) -> bool:
    return bool(material.get("IsPEC", False))


def _kappa(material: dict) -> float:
    return _as_float(material.get("Kappa", 0.0), 0.0)


def _is_conductor(material: dict) -> bool:
    # Accept ideal PEC and finite-conductivity conductors.
    return _is_pec(material) or _kappa(material) > 0.0


def _epsilon_r(material: dict) -> float:
    return _as_float(material.get("EpsilonR", 0.0), 0.0)


def _candidate_material_names(candidate: dict) -> list[str]:
    return [str(name) for name in candidate.get("material_names", []) if str(name).strip()]


def _candidate_materials(candidate: dict, materials_by_name: dict[str, dict]) -> list[dict]:
    return [materials_by_name[name] for name in _candidate_material_names(candidate) if name in materials_by_name]


def _candidate_is_conductor(candidate: dict, materials_by_name: dict[str, dict]) -> bool:
    return any(_is_conductor(material) for material in _candidate_materials(candidate, materials_by_name))


def _has_dielectric_between(
    *,
    r_in: float,
    r_out: float,
    candidates: list[dict],
    materials_by_name: dict[str, dict],
    tol: float,
) -> bool:
    for candidate in candidates:
        radius = _as_float(candidate.get("radius"), 0.0)
        if radius <= r_in + tol or radius >= r_out - tol:
            continue
        for material in _candidate_materials(candidate, materials_by_name):
            if not _is_conductor(material):
                return True
    return False


def _select_conductive_pair(
    *,
    candidates: list[dict],
    materials_by_name: dict[str, dict],
    tol: float,
) -> tuple[dict, dict] | None:
    by_radius = sorted(candidates, key=lambda item: _as_float(item.get("radius"), 0.0))
    conductive = [item for item in by_radius if _candidate_is_conductor(item, materials_by_name)]
    if len(conductive) < 2:
        return None

    best_pair: tuple[dict, dict] | None = None
    best_score: tuple[int, float] | None = None
    for i, inner in enumerate(conductive):
        r_in = _as_float(inner.get("radius"), 0.0)
        for outer in conductive[i + 1 :]:
            r_out = _as_float(outer.get("radius"), 0.0)
            if r_out <= r_in + tol:
                continue

            has_dielectric = _has_dielectric_between(
                r_in=r_in,
                r_out=r_out,
                candidates=by_radius,
                materials_by_name=materials_by_name,
                tol=tol,
            )
            # Prefer pairs with dielectric between; then prefer larger radial gap.
            score = (1 if has_dielectric else 0, r_out - r_in)
            if best_score is None or score > best_score:
                best_score = score
                best_pair = (inner, outer)

    return best_pair


def coax_impedance_ohm(r_in: float, r_out: float, epsilon_r: float) -> float | None:
    """Return coaxial TEM characteristic impedance in Ohms for valid geometric/material inputs."""
    inner = _as_float(r_in, 0.0)
    outer = _as_float(r_out, 0.0)
    eps_r = _as_float(epsilon_r, 0.0)

    if inner <= 0.0 or outer <= inner or eps_r <= 0.0:
        return None

    try:
        value = (60.0 / math.sqrt(eps_r)) * math.log(outer / inner)
    except Exception:
        return None

    if not math.isfinite(value) or value <= 0.0:
        return None
    return value


def infer_coax_from_waveguide_detection(
    *,
    detection: dict | None,
    materials_by_name: dict[str, dict],
) -> dict[str, object]:
    if not detection:
        return {"status": "unsupported", "reason": "missing_detection"}

    if str(detection.get("status", "")) != "supported":
        return {
            "status": "unsupported",
            "reason": "geometry_detection_not_supported",
        }

    if str(detection.get("kind", "")) != "coax_axis_aligned":
        return {
            "status": "unsupported",
            "reason": "unsupported_detection_kind",
        }

    inner = detection.get("inner") or {}
    outer = detection.get("outer") or {}
    r_in = _as_float(inner.get("radius"), 0.0)
    r_out = _as_float(outer.get("radius"), 0.0)
    axis = str(detection.get("axis", "")).strip()

    if axis not in {"x", "y", "z"}:
        return {"status": "unsupported", "reason": "invalid_axis"}
    if r_in <= 0.0 or r_out <= r_in:
        return {"status": "unsupported", "reason": "invalid_radii"}

    tol = max(1e-9, abs(r_out - r_in) * 1e-8)

    # Robustness: if the geometry detector picked a non-conductive inner/outer object,
    # choose the best conductive pair from all concentric candidates.
    detected_candidates = [item for item in detection.get("candidates", []) if isinstance(item, dict)]
    if detected_candidates:
        if not _candidate_is_conductor(inner, materials_by_name) or not _candidate_is_conductor(outer, materials_by_name):
            selected_pair = _select_conductive_pair(
                candidates=detected_candidates,
                materials_by_name=materials_by_name,
                tol=tol,
            )
            if selected_pair is not None:
                inner, outer = selected_pair
                r_in = _as_float(inner.get("radius"), 0.0)
                r_out = _as_float(outer.get("radius"), 0.0)
                tol = max(1e-9, abs(r_out - r_in) * 1e-8)

    inner_material_names = [str(name) for name in inner.get("material_names", []) if str(name).strip()]
    outer_material_names = [str(name) for name in outer.get("material_names", []) if str(name).strip()]

    inner_materials = [materials_by_name[name] for name in inner_material_names if name in materials_by_name]
    outer_materials = [materials_by_name[name] for name in outer_material_names if name in materials_by_name]

    if not any(_is_conductor(material) for material in inner_materials):
        return {"status": "unsupported", "reason": "inner_conductor_not_pec"}
    if not any(_is_conductor(material) for material in outer_materials):
        return {"status": "unsupported", "reason": "outer_conductor_not_pec"}

    dielectric_candidates: list[tuple[float, dict, str]] = []
    for candidate in detection.get("candidates", []):
        radius = _as_float(candidate.get("radius"), 0.0)
        if radius <= r_in + tol or radius >= r_out - tol:
            continue
        for material_name in [str(name) for name in candidate.get("material_names", []) if str(name).strip()]:
            material = materials_by_name.get(material_name)
            if material is None or _is_conductor(material):
                continue
            dielectric_candidates.append((radius, material, material_name))

    if not dielectric_candidates:
        return {
            "status": "unsupported",
            "reason": "dielectric_material_not_found",
        }

    dielectric_candidates.sort(key=lambda item: (-item[0], item[2]))
    _, dielectric_material, dielectric_material_name = dielectric_candidates[0]
    epsilon_r = _epsilon_r(dielectric_material)
    if epsilon_r <= 0.0:
        return {
            "status": "unsupported",
            "reason": "dielectric_epsilon_invalid",
        }

    z0_ohm = coax_impedance_ohm(r_in=r_in, r_out=r_out, epsilon_r=epsilon_r)
    if z0_ohm is None:
        return {
            "status": "unsupported",
            "reason": "coax_impedance_invalid",
        }

    return {
        "status": "supported",
        "kind": "coax_axis_aligned",
        "axis": axis,
        "r_in": r_in,
        "r_out": r_out,
        "dielectric_epsilon_r": epsilon_r,
        "z0_ohm": z0_ohm,
        "inner_conductor_geometry": str(inner.get("geometry_name", "") or ""),
        "outer_conductor_geometry": str(outer.get("geometry_name", "") or ""),
        "dielectric_material_name": dielectric_material_name,
    }


__all__ = ["coax_impedance_ohm", "infer_coax_from_waveguide_detection"]