from __future__ import annotations

from typing import Any


def get_proxy_type(obj: Any) -> str:
    proxy = getattr(obj, "Proxy", None)
    return str(getattr(proxy, "TYPE", ""))


def is_openems_object(obj: Any) -> bool:
    proxy_type = get_proxy_type(obj)
    if proxy_type.startswith("OpenEMS_"):
        return True
    # Fallback for edge cases where Proxy type is not fully restored yet.
    return str(getattr(obj, "Name", "")).startswith("OpenEMS")


def is_assignable_to_analysis(obj: Any) -> bool:
    """Allow OpenEMS objects and external geometry objects with a Shape."""
    if obj is None:
        return False

    proxy_type = get_proxy_type(obj)
    if proxy_type == "OpenEMS_Analysis":
        return False

    if is_openems_object(obj):
        return True

    # Non-OpenEMS geometry (Part/Draft/etc.) is valid export scope if it has a Shape.
    return hasattr(obj, "Shape")


def get_analyses(doc: Any) -> list[Any]:
    if doc is None:
        return []
    return [
        obj
        for obj in getattr(doc, "Objects", [])
        if get_proxy_type(obj) == "OpenEMS_Analysis"
    ]


def get_active_analysis(doc: Any) -> Any | None:
    analyses = get_analyses(doc)
    for analysis in analyses:
        if bool(getattr(analysis, "IsActive", False)):
            return analysis
    return analyses[0] if analyses else None


def set_active_analysis(doc: Any, active_analysis: Any) -> None:
    for analysis in get_analyses(doc):
        analysis.IsActive = analysis == active_analysis


def add_member_to_analysis(analysis: Any, member: Any) -> bool:
    if analysis is None or member is None:
        return False
    if not is_assignable_to_analysis(member):
        return False

    current = list(getattr(analysis, "Group", []))
    if member in current:
        return False

    analysis.addObject(member)
    return True


def assign_members_to_active_analysis(doc: Any, members: list[Any]) -> int:
    analysis = get_active_analysis(doc)
    if analysis is None:
        return 0

    added = 0
    for member in members:
        if add_member_to_analysis(analysis, member):
            added += 1
    return added


def assign_members_to_analysis_detailed(analysis: Any, members: list[Any]) -> dict[str, int]:
    result = {
        "added": 0,
        "already_member": 0,
        "ignored": 0,
    }
    if analysis is None:
        return result

    current = list(getattr(analysis, "Group", []))
    for member in members:
        if member in current:
            result["already_member"] += 1
            continue
        if add_member_to_analysis(analysis, member):
            result["added"] += 1
            current.append(member)
        else:
            result["ignored"] += 1

    return result
