import attrs
import re

from ..path import HashablePath
from ..structures import SubclassRegistry


@attrs.define
class ReadGroup:
    ID: str = attrs.field()
    SM: str = attrs.field()
    LB: str = attrs.field()
    PU: str = attrs.field()
    PL: str = attrs.field()

    def to_string(self, escape_tab: bool = True):
        separator = "\\t" if escape_tab else "\t"
        return separator.join(
            [
                f"ID:{self.ID}",
                f"SM:{self.SM}",
                f"LB:{self.LB}",
                f"PU:{self.PU}",
                f"PL:{self.PL}",
            ]
        )


@attrs.define
class SequencingData:
    """Base class for sequencing data associated with a sample.
    Subclasses represent specific data types (e.g. FASTQ, BAM).
    """

    library: str = attrs.field()
    technology: str = attrs.field()
    instrument: str = attrs.field()
    flowcell: str = attrs.field()
    lane: str = attrs.field()
    sample: object = attrs.field(default=None, eq=False, repr=False, init=False)

    def __hash__(self) -> int:
        return hash(
            (self.library, self.technology, self.instrument, self.flowcell, self.lane)
        )

    @property
    def read_group(self) -> ReadGroup:
        if self.sample is None:
            raise ValueError("Sample is not set for this SequencingData instance.")
        return ReadGroup(
            ID=f"{self.sample.name}.{self.library}.{self.flowcell}.{self.lane}",
            SM=self.sample.name,
            LB=self.library,
            PU=f"{self.flowcell}.{self.lane}",
            PL=self.technology,
        )


@attrs.define
class SingleEndFASTQ(SequencingData):
    file: HashablePath = attrs.field(converter=HashablePath)

    @file.validator
    def check_file(self, attribute, value: HashablePath):
        if not re.search(r"\.(fastq|fq)(\.gz)?$", value.name.lower()):
            raise ValueError(
                f"FASTQ file must have .fastq, .fastq.gz, .fq, or .fq.gz extension, got: {value.suffix}"
            )


@attrs.define
class PairedEndFASTQ(SequencingData):
    r1: HashablePath = attrs.field(converter=HashablePath)
    r2: HashablePath = attrs.field(converter=HashablePath)

    @r1.validator
    def check_r1(self, attribute, value: HashablePath):
        if not re.search(r"\.(fastq|fq)(\.gz)?$", value.name.lower()):
            raise ValueError(
                f"FASTQ r1 file must have .fastq, .fastq.gz, .fq, or .fq.gz extension, got: {value.suffix}"
            )

    @r2.validator
    def check_r2(self, attribute, value: HashablePath):
        if not re.search(r"\.(fastq|fq)(\.gz)?$", value.name.lower()):
            raise ValueError(
                f"FASTQ r2 file must have .fastq, .fastq.gz, .fq, or .fq.gz extension, got: {value.suffix}"
            )


@attrs.define
class Spring(SequencingData):
    files: list[HashablePath] = attrs.field(
        factory=list, converter=lambda x: [HashablePath(f) for f in x]
    )

    @files.validator
    def check_files(self, attribute, value: list[HashablePath]):
        if not value:
            raise ValueError("Spring files list cannot be empty.")
        if not all(re.search(r"\.spring$", f.name.lower()) for f in value):
            suffixes = {f.suffix.lower() for f in value}
            raise ValueError(
                f"All Spring files must have .spring extension, got: {', '.join(suffixes)}"
            )


@attrs.define
class UBAM(SequencingData):
    file: HashablePath = attrs.field(converter=HashablePath)

    @file.validator
    def check_file(self, attribute, value: HashablePath):
        if not re.search(r"\.bam$", value.name.lower()):
            raise ValueError(
                f"Unmapped BAM file must have .bam extension, got: {value.suffix}"
            )


@attrs.define
class UCRAM(SequencingData):
    file: HashablePath = attrs.field(converter=HashablePath)

    @file.validator
    def check_file(self, attribute, value: HashablePath):
        if not re.search(r"\.cram$", value.name.lower()):
            raise ValueError(
                f"Unmapped CRAM file must have .cram extension, got: {value.suffix}"
            )


sequencing_data_registry = SubclassRegistry(
    type=SequencingData,
    single_end_fastq=SingleEndFASTQ,
    paired_end_fastq=PairedEndFASTQ,
    spring=Spring,
    ubam=UBAM,
    ucram=UCRAM,
)


class SequencingDataList(list[SequencingData]):
    def __init__(self, data: list[SequencingData | dict] | None = None):
        super().__init__([_convert_to_sequencing_data(d) for d in data or []])

    def append(self, object):
        return super().append(_convert_to_sequencing_data(object))

    def extend(self, iterable):
        return super().extend(_convert_to_sequencing_data(d) for d in iterable)

    def insert(self, index, object):
        return super().insert(index, _convert_to_sequencing_data(object))

    def subset_by_type(self, *types: type[SequencingData]) -> "SequencingDataList":
        return SequencingDataList([sd for sd in self if isinstance(sd, types)])


def _convert_to_sequencing_data(datum: dict | SequencingData) -> SequencingData:
    # Already converted
    if isinstance(datum, SequencingData):
        return datum

    # Lookup by explicit type
    if (dtype := datum.get("type")) is not None and dtype in sequencing_data_registry:
        sequencing_data_cls = sequencing_data_registry[dtype]
        datum_copy = datum.copy()
        datum_copy.pop("type")
        return sequencing_data_cls(**datum_copy)

    # Infer type by trying each registered class
    for sequencing_data_cls in sequencing_data_registry.values():
        try:
            sd = sequencing_data_cls(**datum)
        except TypeError:
            continue
        return sd
    else:
        raise ValueError(f"Could not determine sequencing data type for: {datum}")
