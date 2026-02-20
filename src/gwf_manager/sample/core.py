import attrs
import hashlib
import json
from enum import Enum
from pathlib import Path

from .metadata import MetadataDict, metadata_registry
from .sequencing_data import SequencingDataList
from ..path import TemporaryPath
from ..utilities import legalize_for_gwf


@attrs.define
class Sample:
    name: str = attrs.field()
    data: SequencingDataList = attrs.field(
        factory=SequencingDataList,
        converter=SequencingDataList,
    )
    metadata: MetadataDict = attrs.field(
        factory=MetadataDict,
        converter=MetadataDict,
    )

    def __attrs_post_init__(self):
        if not self.data:
            raise ValueError(
                f"Sample '{self.name}' must have at least one SequencingData entry."
            )
        for sd in self.data:
            sd.sample = self

    @classmethod
    def from_dict(cls, data: dict) -> "Sample":
        return cls(**data)

    @property
    def legalized_name(self) -> str:
        """GWF target-friendly sample name."""
        return legalize_for_gwf(self.name)

    @property
    def sha256(self) -> str:
        """Calculate SHA256 checksum for all sequencing data read group IDs."""
        sha256 = hashlib.sha256()
        for seq_info in sorted(set(sd.read_group.ID for sd in self.data)):
            sha256.update(str(seq_info).encode("utf-8"))
        return sha256.hexdigest()

    def output_file(self, *parts: str, mkdir: bool = False) -> Path:
        path = Path("output", "samples", self.name, *parts)
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def temp_file(self, *parts: str, mkdir: bool = False) -> TemporaryPath:
        path = TemporaryPath("temp", "samples", self.name, *parts)
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path


class SampleList(list[Sample]):
    def __init__(self, *args: Sample | dict, sample_type=Sample):
        self.sample_type = sample_type

        super().__init__(
            sample_type.from_dict(s) if isinstance(s, dict) else s for s in args
        )

        self._sample_dict = {}
        for sample in self:
            if sample.name in self._sample_dict:
                raise ValueError(f"Duplicate sample name found: '{sample.name}'")
            self._sample_dict[sample.name] = sample

    @classmethod
    def from_file(cls, path: str | Path, sample_type=Sample) -> "SampleList":
        data = json.loads(Path(path).read_text())
        if not isinstance(data, list):
            raise TypeError(
                "Sample list file must contain a JSON array at the top level."
            )
        return cls(*data, sample_type=sample_type)

    def __delitem__(self, key):
        del self._sample_dict[self[key].name]
        super().__delitem__(key)

    @property
    def sha256(self) -> str:
        sha256 = hashlib.sha256()
        for sample in sorted(self, key=lambda s: s.name):
            sha256.update(sample.sha256.encode("utf-8"))
        return sha256.hexdigest()

    def append(self, item: Sample) -> None:
        if item.name in self._sample_dict:
            raise ValueError(
                f"Sample with name '{item.name}' already exists in the list."
            )
        self._sample_dict[item.name] = item
        super().append(item)

    def extend(self, items: list[Sample]) -> None:
        for item in items:
            if item.name in self._sample_dict:
                raise ValueError(
                    f"Sample with name '{item.name}' already exists in the list."
                )
        for item in items:
            self._sample_dict[item.name] = item
        super().extend(items)

    def insert(self, index: int, item: Sample) -> None:
        if item.name in self._sample_dict:
            raise ValueError(
                f"Sample with name '{item.name}' already exists in the list."
            )
        self._sample_dict[item.name] = item
        super().insert(index, item)

    def subset_by_names(self, *names: str) -> "SampleList":
        """Subset samples by their names.

        Args:
            *names (str): The names of the samples to include in the subset.

        Returns:
            A SampleList of Sample instances with the specified names.
        """
        return SampleList(
            *(self._sample_dict[name] for name in names),
            sample_type=self.sample_type,
        )

    def subset_by_metadata(self, *metadata: Enum) -> "SampleList":
        """Subset samples by metadata values.

        Args:
            *metadata (Enum): Metadata values to filter samples by.

        Returns:
            A SampleList of Sample instances that match all specified metadata criteria.
        """
        result = SampleList(sample_type=self.sample_type)
        for sample in self:
            sample_metadata = set(sample.metadata.values())
            if all(m in sample_metadata for m in metadata):
                result.append(sample)
        return result
