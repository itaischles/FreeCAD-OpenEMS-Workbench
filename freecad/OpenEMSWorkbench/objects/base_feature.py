from __future__ import annotations

from typing import Any


class FeatureProxyBase:
    """Reusable base for serialization-safe FeaturePython proxies."""

    TYPE = "OpenEMS_Base"
    VERSION = 1

    def __init__(self) -> None:
        self._is_restoring = False

    def attach(self, obj: Any) -> None:
        obj.Proxy = self
        self.ensure_properties(obj)
        self.initialize_defaults(obj)

    def ensure_properties(self, obj: Any) -> None:
        raise NotImplementedError

    def initialize_defaults(self, obj: Any) -> None:
        """Set defaults only if the property is empty or missing."""

    def execute(self, obj: Any) -> None:
        """Default recompute hook."""

    def onChanged(self, obj: Any, prop: str) -> None:  # noqa: N802 - FreeCAD API
        _ = (obj, prop)

    def onDocumentRestored(self, obj: Any) -> None:  # noqa: N802 - FreeCAD API
        self._is_restoring = True
        self.ensure_properties(obj)
        self.initialize_defaults(obj)
        self._is_restoring = False

    def dumps(self) -> dict[str, Any]:
        return {"type": self.TYPE, "version": self.VERSION}

    def loads(self, state: dict[str, Any]) -> None:
        _ = state


class ViewProviderBase:
    """Reusable base for ViewProvider proxies."""

    TYPE = "OpenEMS_BaseView"

    def attach(self, vobj: Any) -> None:
        self.Object = getattr(vobj, "Object", None)

    def getDisplayModes(self, obj: Any) -> list[str]:  # noqa: N802 - FreeCAD API
        _ = obj
        return []

    def getDefaultDisplayMode(self) -> str:  # noqa: N802 - FreeCAD API
        return "Flat Lines"

    def setDisplayMode(self, mode: str) -> str:  # noqa: N802 - FreeCAD API
        return mode

    def claimChildren(self) -> list[Any]:  # noqa: N802 - FreeCAD API
        return []

    def dumps(self) -> dict[str, Any]:
        return {"type": self.TYPE}

    def loads(self, state: dict[str, Any]) -> None:
        _ = state


def add_property_if_missing(
    obj: Any,
    prop_type: str,
    prop_name: str,
    group: str,
    description: str,
    default: Any,
) -> None:
    if hasattr(obj, prop_name):
        return
    obj.addProperty(prop_type, prop_name, group, description)
    try:
        setattr(obj, prop_name, default)
    except Exception:
        # Enumeration properties may reject assignment before choices are defined.
        pass


def set_enum_choices(obj: Any, prop_name: str, choices: list[str], default: str) -> None:
    current = getattr(obj, prop_name, None)
    setattr(obj, prop_name, choices)
    if current in choices:
        setattr(obj, prop_name, current)
    else:
        setattr(obj, prop_name, default)
