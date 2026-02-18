import attrs
import json
from enum import Enum
from pathlib import Path

from .addon import AddonDict, addon_registry
from ..sample import SampleList


@attrs.define
class Analysis:
    kind: Enum = attrs.field(converter=lambda k: analysis_kind_enum[k])
    addons: AddonDict = attrs.field(factory=AddonDict, converter=AddonDict)
    samples: SampleList = attrs.field(factory=SampleList, converter=SampleList)


analysis_type: type[Analysis] = Analysis
analysis_kind_enum: Enum | None = None


class AnalysisList(list[Analysis]):
    def __init__(
        self,
        sample_list: SampleList,
        *analyses: dict | Analysis,
    ):
        assert (
            analysis_kind_enum is not None
        ), "Analysis kind enum must be set up before creating AnalysisList instances."

        self.sample_list = sample_list

        parsed_analyses = []
        for datum in analyses:
            if isinstance(datum, Analysis):
                parsed_analyses.append(datum)
                continue

            samples = SampleList(
                *(self.sample_list.get_by_name(s) for s in datum.pop("samples")),
                sample_type=self.sample_list.sample_type,
            )
            addons = {
                k: [addon_registry[k][v] for v in li]
                for k, li in datum.pop("addons", {}).items()
            }

            parsed_analyses.append(
                analysis_type(
                    kind=analysis_kind_enum[datum.pop("kind")],
                    addons=addons,
                    samples=samples,
                    **datum,
                )
            )
        super().__init__(parsed_analyses)

    @classmethod
    def from_path(cls, path: str | Path, sample_list: SampleList) -> "AnalysisList":
        """
        Create an AnalysisList from a JSON file.

        Args:
            path: The path to the JSON file containing the analysis specifications.
            sample_list: A SampleList instance to be used for creating Analysis objects.

        Returns:
            An AnalysisList instance containing the analyses specified in the JSON file.
        """
        analyses = json.loads(Path(path).read_text())
        return cls(sample_list=sample_list, *analyses)

    def subset_by_kind(
        self,
        *analysis_kind: Enum,
    ) -> "AnalysisList":
        """Subset analyses by kind.

        Args:
            *analysis_kind (Enum): One or more analysis kinds to filter by.

        Returns:
            An AnalysisList containing only analyses of the specified kinds.
        """
        return AnalysisList(
            sample_list=self.sample_list,
            *[a for a in self if a.kind in analysis_kind],
        )

    def subset_by_addon(
        self,
        *addon: Enum,
    ) -> "AnalysisList":
        """Subset analyses by addon.

        Args:
            *addon (Enum): One or more addons to filter by.

        Returns:
            An AnalysisList containing only analyses with the specified addons.
        """
        return AnalysisList(
            sample_list=self.sample_list,
            *[a for a in self if a.addons.has(*addon)],
        )
