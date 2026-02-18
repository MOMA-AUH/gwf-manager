from enum import Enum

from .core import Sample, SampleList
from .metadata import metadata_registry
from .sequencing_data import SequencingData, sequencing_data_registry


def setup_sample_module(
    metadata: dict[str, Enum] | None = None,
    sequencing_data: dict[str, Enum] | None = None,
    sample_cls: type[Sample] = Sample,
) -> None:
    """Configure the sample module with specific types.

    Args:
        metadata (dict): Optional dict mapping metadata keys to Enum classes.
        sequencing_data (dict): Optional dict mapping sequencing data keys to Enum classes.
        sample_cls (type): Class to use for Sample instances (default: Sample).
    """
    global sample_type
    sample_type = sample_cls

    if metadata is not None:
        metadata_registry.clear()
        metadata_registry.update(metadata)

    if sequencing_data is not None:
        sequencing_data_registry.clear()
        sequencing_data_registry.update(sequencing_data)


__all__ = [
    "Sample",
    "SampleList",
    "SequencingData",
    "setup_sample_module",
    "metadata_registry",
    "sequencing_data_registry",
]
