from collections import defaultdict
from enum import Enum
from typing import Iterable, Any

from ..structures import SubclassRegistry


addon_registry = SubclassRegistry(type=Enum)


class AddonDict(defaultdict[str, set[Enum]]):
    """Stores addons grouped by key.

    - Keys registered in `addon_registry` must use Enum values.
    - String values are automatically converted to Enum members.
    - Multiple values per key are supported.
    """

    def __init__(self) -> None:
        super().__init__(set)

    def __setitem__(self, key: str, value: str | Enum | Iterable[str | Enum]) -> None:
        self[key].clear()

        if isinstance(value, (str, Enum)):
            self.add(key, value)
        else:
            self.update(key, value)

    def add(self, key: str, value: str | Enum) -> None:
        super().__getitem__(key).add(_normalize(key, value))

    def update(self, key: str, values: Iterable[str | Enum]) -> None:
        for value in values:
            self.add(key, value)

    def has(self, *addon: Enum) -> bool:
        return any(set().union(*self.values()).intersection(addon))


def _normalize(key: str, value: str | Enum) -> Enum | Any:
    """Validate and convert value based on registry rules."""

    if key not in addon_registry:
        return value

    enum_cls = addon_registry[key]

    if isinstance(value, str):
        try:
            return enum_cls[value]
        except KeyError:
            valid = ", ".join(e.name for e in enum_cls)
            raise ValueError(
                f"Invalid value '{value}' for addon key '{key}'. "
                f"Valid options: {valid}"
            ) from None

    if isinstance(value, enum_cls):
        return value

    raise TypeError(
        f"Value for addon key '{key}' must be str or {enum_cls.__name__}, "
        f"got {type(value).__name__}."
    )
