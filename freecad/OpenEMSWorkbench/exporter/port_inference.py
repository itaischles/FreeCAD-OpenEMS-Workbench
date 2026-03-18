from __future__ import annotations


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _is_pec(material: dict) -> bool:
    return bool(material.get("IsPEC", False))


def _epsilon_r(material: dict) -> float:
    return _as_float(material.get("EpsilonR", 0.0), 0.0)


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

    inner_material_names = [str(name) for name in inner.get("material_names", []) if str(name).strip()]
    outer_material_names = [str(name) for name in outer.get("material_names", []) if str(name).strip()]

    inner_materials = [materials_by_name[name] for name in inner_material_names if name in materials_by_name]
    outer_materials = [materials_by_name[name] for name in outer_material_names if name in materials_by_name]

    if not any(_is_pec(material) for material in inner_materials):
        return {"status": "unsupported", "reason": "inner_conductor_not_pec"}
    if not any(_is_pec(material) for material in outer_materials):
        return {"status": "unsupported", "reason": "outer_conductor_not_pec"}

    tol = max(1e-9, abs(r_out - r_in) * 1e-8)
    dielectric_candidates: list[tuple[float, dict, str]] = []
    for candidate in detection.get("candidates", []):
        radius = _as_float(candidate.get("radius"), 0.0)
        if radius <= r_in + tol or radius >= r_out - tol:
            continue
        for material_name in [str(name) for name in candidate.get("material_names", []) if str(name).strip()]:
            material = materials_by_name.get(material_name)
            if material is None or _is_pec(material):
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

    return {
        "status": "supported",
        "kind": "coax_axis_aligned",
        "axis": axis,
        "r_in": r_in,
        "r_out": r_out,
        "dielectric_epsilon_r": epsilon_r,
        "inner_conductor_geometry": str(inner.get("geometry_name", "") or ""),
        "outer_conductor_geometry": str(outer.get("geometry_name", "") or ""),
        "dielectric_material_name": dielectric_material_name,
    }


__all__ = ["infer_coax_from_waveguide_detection"]