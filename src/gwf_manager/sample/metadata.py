from enum import Enum

from ..structures import SubclassRegistry


metadata_registry = SubclassRegistry(type=Enum)


class MetadataDict(dict):
    """A dictionary for storing sample metadata with automatic type conversion based on the metadata registry."""

    def __setitem__(self, key, value):
        if key in metadata_registry:
            enum_cls = metadata_registry[key]
            if isinstance(value, str):
                try:
                    value = enum_cls[value]
                except KeyError:
                    raise ValueError(
                        f"Invalid value '{value}' for metadata key '{key}'. Valid options are: {[e.name for e in enum_cls]}"
                    )
            elif not isinstance(value, enum_cls):
                raise ValueError(
                    f"Value for metadata key '{key}' must be a string or an instance of {enum_cls.__name__}."
                )
        super().__setitem__(key, value)
