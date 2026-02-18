import logging

try:
    import gwf
except ImportError:
    logging.debug("GWF not found. Some functionality may be limited.")

from .analysis import Analysis, AnalysisList, setup_analysis_module
from .config import parameters, reference, resources
from .decorators import cache_task, use_wd_scratch, use_custom_scratch
from .manager import Manager
from .sample import Sample, SampleList, setup_sample_module

__all__ = [
    "Analysis",
    "AnalysisList",
    "Manager",
    "Sample",
    "SampleList",
    "cache_task",
    "setup_analysis_module",
    "setup_sample_module",
    "use_custom_scratch",
    "use_wd_scratch",
    "parameters",
    "reference",
    "resources",
]
