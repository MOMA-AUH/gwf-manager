# gwf-manager

A high-level framework for building reproducible bioinformatics workflows with [gwf](https://gwf.app/). `gwf-manager` provides structured abstractions for samples, analyses, task caching, scratch directory management, and Conda-based execution — making it easier to write and maintain large-scale genomics pipelines.

## Installation

**Requirements:** Python ≥ 3.8, [gwf](https://gwf.app/) ≥ 2.0, [attrs](https://www.attrs.org/) ≥ 23.0

### As a package

```bash
pip install git+https://github.com/MOMA-AUH/gwf-manager.git
```

### As a git submodule

```bash
git submodule add https://github.com/MOMA-AUH/gwf-manager.git submodules/gwf_manager
```

## Quick start

```python
from gwf import Workflow
from gwf_manager import Manager, Sample, SampleList

gwf = Workflow()

samples = SampleList.from_file("input/samples.json")

with Manager(gwf) as manager:
    for sample in samples:
        template = ...  # build your AnonymousTarget
        manager.submit(name=f"align_{sample.name}", template=template, task_id=None)
```

When the `with` block exits, the `Manager` automatically finalises the workflow — submitting all registered targets to gwf and appending a clean-up target that removes temporary directories.

### Project structure

A typical pipeline using `gwf-manager` follows this layout:

```
.managerconf.json         # Optional overrides for default paths
input/
├── parameters.json       # Pipeline parameters
├── reference.json        # Reference file paths
├── resources.json        # Cluster resource defaults (cores, memory, walltime)
├── samples.json          # Sample definitions
├── analyses.json         # Analysis definitions
└── conda/                # Conda environment YAMLs
    ├── env_a.yaml
    └── env_b.yaml
workflow.py               # gwf workflow entry point
```

## Core concepts

### Manager

The `Manager` class is the central orchestrator. It wraps a gwf `Workflow` and provides:

| Capability | Description |
|---|---|
| **Target tracking** | Deduplicates targets by name — resubmitting a target with an identical spec is safe; differing specs raise an error. |
| **Task grouping** | Targets can be grouped into *tasks* via a `task_id`. A task can be marked as *should not submit* (e.g. by the caching decorator) to skip all of its targets at once. |
| **Clean-up target** | Optionally appends a final target that removes `temp/` and `scratch/` directories after all other work completes. |
| **Path helpers** | Convenience methods (`output_dir`, `output_file`, `temp_dir`, `temp_file`) for building structured output and temporary paths. |

```python
with Manager(gwf, clean_up=True) as manager:
    ...
```

> **Note:** Configuration loading and Conda environment setup happen automatically at import time (see [Configuration](#configuration) and [Conda executors](#conda-executors) below). The `Manager` itself only needs the gwf `Workflow` instance.

#### Default paths

| Key | Default path |
|---|---|
| `parameters_json` | `input/parameters.json` |
| `reference_json` | `input/reference.json` |
| `resources_json` | `input/resources.json` |
| `conda_config_dir` | `input/conda` |

#### Overriding defaults with `.managerconf.json`

Place a `.managerconf.json` file in the working directory (or any parent directory) to override any of the default paths:

```json
{
    "parameters_json": "config/my_parameters.json",
    "conda_config_dir": "config/conda",
    "conda_envs_dir": "/shared/conda_envs"
}
```

`gwf-manager` searches upward from the current working directory for the first `.managerconf.json` it finds. Values from the file take precedence over the built-in defaults via a `ChainMap`.

### Configuration

When `gwf_manager` is first imported, three global `Configuration` objects are populated from JSON files:

```python
from gwf_manager import parameters, reference, resources
```

Each is a dict subclass that supports nested key access:

```python
# reference.json: {"genome": {"fasta": "/refs/hg38.fa"}}
reference.get_in("genome", "fasta")  # returns "/refs/hg38.fa"
```

Configurations are loaded once; subsequent calls to `load()` are silently ignored to prevent accidental overwrites.

### Conda executors

`gwf-manager` automatically discovers Conda environment YAML files (`.yaml` / `.yml`) in the configured `conda_config_dir` and creates **content-addressed** environments in `conda_envs_dir`. An SHA256 hash of the YAML content is appended to the environment name, so any change to the YAML triggers a fresh environment build while old environments remain intact.

Discovered executors are stored in a global `executor_registry` and can be referenced by YAML stem name:

```python
from gwf_manager import executor_registry

conda_env = executor_registry["env_a"]  # Conda instance for env_a.yaml
```

### Decorators

#### `@cache_task` — SHA256-based task caching

Wraps a task function so that it is only submitted when its inputs or outputs have changed. The decorator computes a SHA256 hash from the sample's read group IDs and the task's declared outputs, then compares it against a cached hash on disk.

```python
from gwf_manager import cache_task

@cache_task
def align(*, manager, sample, task_id, **kwargs):
    template = ...  # build AnonymousTarget
    manager.submit(name=f"align_{sample.name}", template=template, task_id=task_id)
    return {"bam": str(sample.output_file("aligned.bam"))}
```

If the hash matches the cached value, all targets in the task are skipped.

#### `@use_wd_scratch` / `@use_custom_scratch` — scratch directory management

These decorators augment a target's shell spec to execute inside a scratch directory. Inputs are symlinked in, outputs are moved out, and the scratch directory is cleaned up afterwards.

```python
from gwf_manager import use_wd_scratch, use_custom_scratch

@use_wd_scratch
def my_template(**kwargs):
    return AnonymousTarget(inputs=..., outputs=..., options=..., spec=...)

@use_custom_scratch("/scratch/my_job")
def my_other_template(**kwargs):
    return AnonymousTarget(inputs=..., outputs=..., options=..., spec=...)
```

`@use_wd_scratch` creates the scratch directory relative to the working directory at `scratch/<function_name>/$SLURM_JOB_ID`.

### Sample

A `Sample` bundles a sample name with one or more sequencing data entries and optional metadata.

```python
from gwf_manager import Sample, SampleList

samples = SampleList.from_file("input/samples.json")
```

**Sequencing data types** — built-in and registered automatically:

| Type | Fields |
|---|---|
| `PairedEndFASTQ` | `r1`, `r2` |
| `SingleEndFASTQ` | `file` |
| `Spring` | `files` |
| `UBAM` | `file` |
| `UCRAM` | `file` |

All types share common fields: `library`, `technology`, `instrument`, `flowcell`, and `lane`, which are used to construct SAM-spec read groups (`@RG`).

**Metadata** — samples can carry typed metadata backed by Enum classes:

```python
from enum import Enum, auto
from gwf_manager import setup_sample_module

class SampleKind(Enum):
    NORMAL = auto()
    TUMOR = auto()

class MaterialKind(Enum):
    DNA = auto()
    RNA = auto()

setup_sample_module(metadata={"sample_kind": SampleKind, "material_kind": MaterialKind})
```

String values in the input JSON are automatically converted to the corresponding Enum member.

**Subsetting** — `SampleList` supports filtering by name or metadata:

```python
subset = samples.subset_by_names("SampleA", "SampleB")
dna_samples  = samples.subset_by_metadata(MaterialKind.DNA)
```

**SHA-256 checksums** — each `Sample` and `SampleList` exposes a `sha256` property derived from read group IDs, useful for change detection and caching.

#### Example `input/samples.json`

```json
[
    {
        "name": "BloodSample",
        "metadata": {
            "sample_kind": "NORMAL",
            "material_kind": "DNA"
        },
        "data": [
            {
                "library": "SomeLibrary",
                "technology": "Illumina",
                "instrument": "SomeInstrument",
                "flowcell": "SomeFlowcell",
                "lane": "1",
                "r1": "/SomeInstrument/SomeFlowcell/BloodSample_SomeLibrary_L001_R1_001.fastq.gz",
                "r2": "/SomeInstrument/SomeFlowcell/BloodSample_SomeLibrary_L001_R2_001.fastq.gz"
            }
        ]
    },
    {
        "name": "TumorBiopsyDNA",
        "metadata": {
            "sample_kind": "TUMOR",
            "material_kind": "DNA"
        },
        "data": [
            {
                "library": "AnotherLibrary",
                "technology": "Illumina",
                "instrument": "AnotherInstrument",
                "flowcell": "AnotherFlowcell",
                "lane": "1",
                "r1": "/AnotherIntrument/AnotherFlowcell/TumorBiopsy_AnotherLibrary_L001_R1_001.fastq.gz",
                "r2": "/AnotherIntrument/AnotherFlowcell/TumorBiopsy_AnotherLibrary_L001_R2_001.fastq.gz"
            },
            {
                "library": "AnotherLibrary",
                "technology": "Illumina",
                "instrument": "AnotherInstrument",
                "flowcell": "AnotherFlowcell",
                "lane": "2",
                "r1": "/AnotherIntrument/AnotherFlowcell/TumorBiopsy_AnotherLibrary_L002_R1_001.fastq.gz",
                "r2": "/AnotherIntrument/AnotherFlowcell/TumorBiopsy_AnotherLibrary_L002_R2_001.fastq.gz"
            }
        ]
    },
    {
        "name": "TumorBiopsyRNA",
        "metadata": {
            "sample_kind": "TUMOR",
            "material_kind": "RNA"
        },
        "data": [
            {
                "library": "YetAnotherLibrary",
                "technology": "Illumina",
                "instrument": "SomeInstrument",
                "flowcell": "SomeFlowcell",
                "lane": "1",
                "r1": "/SomeInstrument/SomeFlowcell/TumorBiopsyRNA_YetAnotherLibrary_L001_R1_001.fastq.gz",
                "r2": "/SomeInstrument/SomeFlowcell/TumorBiopsyRNA_YetAnotherLibrary_L001_R2_001.fastq.gz"
            }
        ]
    },
    {
        "name": "AnotherTumorBiopsyDNA",
        "metadata": {
            "sample_kind": "TUMOR",
            "material_kind": "DNA"
        },
        "data": [
            {
                "library": "2xYetAnotherLibrary",
                "technology": "Illumina",
                "instrument": "SomeInstrument",
                "flowcell": "YetAnotherFlowcell",
                "lane": "1",
                "files": [
                    "/SomeInstrument/YetAnotherFlowcell/AnotherTumorBiopsyDNA_2xYetAnotherLibrary_L001.spring"
                ]
            },
            {
                "library": "2xYetAnotherLibrary",
                "technology": "Illumina",
                "instrument": "SomeInstrument",
                "flowcell": "YetAnotherFlowcell",
                "lane": "2",
                "files": [
                    "/SomeInstrument/YetAnotherFlowcell/AnotherTumorBiopsyDNA_2xYetAnotherLibrary_L002.spring"
                ]
            }
        ]
    }
]
```

### Analysis

An `Analysis` groups a *kind* (an Enum member), optional *addons*, and a list of `Sample` objects. This is useful for pipelines that run different analysis types (e.g. germline, somatic (paired tumor-normal), somatic (tumor-only)) over subsets of samples.

```python
from enum import Enum, auto()
from gwf_manager import setup_analysis_module, AnalysisList

class AnalysisKind(Enum):
    GERMLINE = auto()
    SOMATIC_TUMOR_NORMAL = auto()
    SOMATIC_TUMOR_ONLY = auto()

setup_analysis_module(kind=AnalysisKind)

analyses = AnalysisList.from_file("input/analyses.json", sample_list=samples)
```

**Addons** let you attach optional flags or features to analyses:

```python
class Caller(Enum):
    FREEBAYES = auto()
    DEEPVARIANT = auto()
    DEEPSOMATIC = auto()

setup_analysis_module(kind=AnalysisKind, addons={"caller": Caller})
```

**Subsetting** — filter by kind or addon:

```python
germline_analyses = analyses.subset_by_kind(AnalysisKind.GERMLINE)
analyses_with_deepvariant_addon  = analyses.subset_by_addon(Caller.DEEPVARIANT)
```

#### Example `input/analyses.json`

```json
[
    {
        "samples": [
            "BloodSample"
        ],
        "kind": "GERMLINE",
        "addons": {
            "caller": ["DEEPVARIANT"]
        }
    },
    {
        "samples": [
            "BloodSample",
            "TumorBiopsyDNA",
            "TumorBiopsyRNA"
        ],
        "kind": "SOMATIC_TUMOR_NORMAL",
        "addons": {
            "caller": ["DEEPSOMATIC"]
        }
    },
    {
        "samples": [
            "AnotherTumorBiopsyDNA"
        ],
        "kind": "SOMATIC_TUMOR_ONLY"
    }
]
```

## License

[MIT](LICENSE)