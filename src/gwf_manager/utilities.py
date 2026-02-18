import inspect
from pathlib import Path


def legalize_for_gwf(name: str) -> str:
    return name.replace("-", "_")


def get_function_name() -> str:
    return inspect.currentframe().f_back.f_code.co_name


def flatten(obj: Path | dict | list) -> list[Path]:
    p = []
    if isinstance(obj, dict):
        for v in obj.values():
            p.extend(flatten(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            p.extend(flatten(item))
    else:
        p.append(Path(obj))
    return p
