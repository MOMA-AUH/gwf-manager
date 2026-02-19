from enum import Enum

from .core import Analysis, AnalysisList, analysis_kind_enum
from .addon import addon_registry


def setup_analysis_module(
    kind: Enum,
    addons: dict[str, Enum] | None = None,
) -> None:
    """Configure the analysis module with specific types.

    Args:
        kind: Enum class defining analysis kinds.
        addons: Optional dict mapping addon keys to Enum classes.
    """
    global analysis_kind_enum
    analysis_kind_enum = kind

    if addons is not None:
        addon_registry.clear()
        addon_registry.update(addons)


__all__ = [
    "Analysis",
    "AnalysisList",
    "setup_analysis_module",
    "addon_registry",
]
