import attrs
import hashlib
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from .structures import InstanceRegistry


YAML_EXTENSIONS = ("*.yaml", "*.yml")

_conda_exe = None


@attrs.define
class Conda:
    """Executes a target in a Conda environment."""

    env: str = attrs.field()
    debug_mode: bool = attrs.field(default=False)

    @property
    def is_path(self) -> bool:
        return "/" in self.env or "\\" in self.env

    def get_command(self, spec_path: str, workflow_root: str) -> Iterable[str]:
        global _conda_exe
        if _conda_exe is None:
            _find_conda_executable()
        debug_flags = ["--debug-wrapper-scripts", "-vvv"] if self.debug_mode else []
        return [
            str(_conda_exe),
            "run",
            "--live-stream",
            *debug_flags,
            "-p" if self.is_path else "-n",
            self.env,
            spec_path,
        ]


def _find_conda_executable() -> Path:
    global _conda_exe
    if (conda_exe := shutil.which("mamba") or shutil.which("conda")) is None:
        raise EnvironmentError("Neither 'mamba' nor 'conda' is installed.")
    if not (conda_exe_path := Path(conda_exe)).exists():
        raise EnvironmentError(f"Conda executable not found at {conda_exe_path}.")
    _conda_exe = conda_exe_path


def _get_or_create_conda_env(yaml: Path, envs_dir: Path) -> Path:
    if not yaml.exists():
        raise FileNotFoundError(f"Conda environment YAML not found at {yaml}")

    name = yaml.stem
    md5 = hashlib.md5(yaml.read_bytes()).hexdigest()

    # Create the environment if it doesn't already exist
    if not (env := envs_dir.joinpath(f"{name}_{md5}")).exists():
        subprocess.check_call(
            [
                str(_conda_exe),
                "env",
                "create",
                "-f",
                str(yaml),
                "-p",
                str(env),
            ]
        )

    return Conda(env=str(env.resolve()))


def setup_conda_executors(
    registry: InstanceRegistry,
    config_dir: str | Path | None,
    envs_dir: str | Path | None,
) -> None:
    if config_dir is None or envs_dir is None:
        logging.debug(
            "Conda configuration directory or environments directory not specified. Skipping Conda executor setup."
        )
        return
    _find_conda_executable()
    config_dir = Path(config_dir)
    envs_dir = Path(envs_dir)
    envs_dir.mkdir(parents=True, exist_ok=True)
    for ext in YAML_EXTENSIONS:
        for yaml in config_dir.glob(ext):
            registry[yaml.stem] = _get_or_create_conda_env(yaml, envs_dir)
