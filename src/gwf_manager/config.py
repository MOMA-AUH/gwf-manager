import json
import logging
from pathlib import Path
from typing import Any


def _get_recursive(current_data: dict, path: list[str], full_path: list[str]) -> Any:
    """Recursively traverse the nested dictionary structure."""
    if not path:
        return current_data

    key = path[0]
    remaining_path = path[1:]

    if key not in current_data:
        path_str = " -> ".join(full_path[: len(full_path) - len(path) + 1])
        raise KeyError(f"Resource key '{key}' not found at path: {path_str}")

    next_value = current_data[key]

    # If there are more keys to traverse but the current value is not a dict
    if remaining_path and not isinstance(next_value, dict):
        path_str = " -> ".join(full_path[: len(full_path) - len(path) + 1])
        raise TypeError(
            f"Cannot traverse further: value at '{path_str}' is {type(next_value).__name__}, not a dictionary"
        )

    return _get_recursive(next_value, remaining_path, full_path)


class Configuration(dict):
    """A dictionary subclass for managing nested configurations."""

    def load(self, path: str | Path) -> None:
        if self:
            logging.debug("Configuration has already been set and cannot be modified.")
            return
        d = json.loads(Path(path).read_text())
        if not isinstance(d, dict):
            raise TypeError(
                "Configuration file must contain a JSON object at the top level."
            )
        self.update(d)

    def get_in(self, *keys: str) -> Any:
        """Get a value from the configuration using a sequence of keys.

        Args:
            *keys: A sequence of keys representing the path to the desired value.

        Returns:
            The value at the specified path in the configuration dictionary.

        Raises:
            KeyError: If any key in the path is not found in the configuration dictionary.
            TypeError: If a non-dictionary value is encountered before reaching the end of the path.
        """
        return _get_recursive(self, keys, keys)


reference = Configuration()
resources = Configuration()
parameters = Configuration()
