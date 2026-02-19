import json
import logging
from collections import ChainMap
from pathlib import Path

from .executors import setup_conda_executors
from .structures import Configuration, InstanceRegistry


DEFAULTS = {
    "parameters_json": "input/parameters.json",
    "reference_json": "input/reference.json",
    "resources_json": "input/resources.json",
    "conda_config_dir": "input/conda",
}


def _locate_config(name: str) -> Path | None:
    working_dir = Path.cwd()
    for parent in [working_dir] + list(working_dir.parents):
        candidate = parent / name
        if candidate.exists():
            return candidate
    else:
        logging.debug(
            f"Configuration file '{name}' not found in {working_dir} or any parent directories."
        )
        return None


def _load_config(path: Path | None) -> dict:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as e:
        logging.error(f"Failed to load configuration from {path}: {e}")
        return {}


config_path = _locate_config(".managerconf.json")
config_dict = _load_config(config_path)

config = ChainMap(config_dict, DEFAULTS)

parameters = Configuration.from_file(config["parameters_json"])
reference = Configuration.from_file(config["reference_json"])
resources = Configuration.from_file(config["resources_json"])

executor_registry = InstanceRegistry(type=object)
setup_conda_executors(
    executor_registry, config["conda_config_dir"], config["conda_envs_dir"]
)

__all__ = ["config", "executor_registry", "parameters", "reference", "resources"]
