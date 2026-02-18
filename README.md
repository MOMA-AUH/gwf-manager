# gwf-manager

A high-level framework for building reproducible bioinformatics workflows with [gwf](https://gwf.app/). `gwf-manager` provides structured abstractions for samples, analyses, task caching, scratch directory management, and Conda-based execution — making it easier to write and maintain large-scale genomics pipelines.

## Installation

```bash
pip install gwf-manager
```

**Requirements:** Python ≥ 3.8, [gwf](https://gwf.app/) ≥ 2.0, [attrs](https://www.attrs.org/) ≥ 23.0

## Quick start

```python
from gwf import Workflow
from gwf_manager import Manager, Sample, SampleList

gwf = Workflow()

samples = SampleList.from_path("input/samples.json")

with Manager(gwf) as manager:
    for sample in samples:
        template = ...  # build your AnonymousTarget
        manager.submit(name=f"align_{sample.name}", template=template, task_id=None)
```

When the `with` block exits, the `Manager` automatically finalises the workflow — submitting all registered targets to gwf and appending a clean-up target that removes temporary directories.

---

## Core concepts

### Manager

The `Manager` class is the central orchestrator. It wraps a gwf `Workflow` and provides:

| Capability | Description |
|---|---|
| **Target tracking** | Deduplicates targets by name — resubmitting a target with an identical spec is safe; differing specs raise an error. |
| **Task grouping** | Targets can be grouped into *tasks* via a `task_id`. A task can be marked as *should not submit* (e.g. by the caching decorator) to skip all of its targets at once. |
| **Configuration loading** | Automatically loads `parameters.json`, `reference.json`, and `resources.json` from an `input/` directory. |
| **Conda integration** | Discovers Conda environment YAML files in `input/conda/` and creates content-addressed environments in `conda_envs/`. |
| **Clean-up target** | Optionally appends a final target that removes `temp/` and `scratch/` directories after all other work completes. |
| **Path helpers** | Convenience methods (`output_dir`, `output_file`, `temp_dir`, `temp_file`) for building structured output and temporary paths. |

```python
with Manager(
    gwf,
    clean_up=True,
    parameters_json="input/parameters.json",
    reference_json="input/reference.json",
    resources_json="input/resources.json",
    conda_config_dir="input/conda",
    conda_envs_dir="conda_envs",
) as manager:
    ...
```

---

### Configuration

Three global `Configuration` objects are available for storing pipeline-wide settings loaded from JSON files:

```python
from gwf_manager import parameters, reference, resources
```

Each is a dict subclass that supports nested key access:

```python
# reference.json: {"genome": {"fasta": "/refs/hg38.fa"}}
reference.get_in("genome", "fasta")  # returns "/refs/hg38.fa"
```

Configurations are loaded once; subsequent calls to `load()` are silently ignored to prevent accidental overwrites.

---

### Sample

A `Sample` bundles a sample name with one or more sequencing data entries and optional metadata.

```python
from gwf_manager import Sample, SampleList

samples = SampleList.from_path("input/samples.json")
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
from enum import Enum
from gwf_manager import setup_sample_module

class Sex(Enum):
    male = "male"
    female = "female"

setup_sample_module(metadata={"sex": Sex})
```

String values in the input JSON are automatically converted to the corresponding Enum member.

**Subsetting** — `SampleList` supports filtering by name or metadata:

```python
subset = samples.subset_by_names("SampleA", "SampleB")
males  = samples.subset_by_metadata(sex="male")
```

**SHA-256 checksums** — each `Sample` and `SampleList` exposes a `sha256` property derived from read group IDs, useful for change detection and caching.

---

### Analysis

An `Analysis` groups a *kind* (an Enum member), optional *addons*, and a list of `Sample` objects. This is useful for pipelines that run different analysis types (e.g. WGS, WES, RNA-seq) over subsets of samples.

```python
from enum import Enum
from gwf_manager import setup_analysis_module, AnalysisList

class AnalysisKind(Enum):
    wgs = "wgs"
    wes = "wes"

setup_analysis_module(kind=AnalysisKind)

analyses = AnalysisList.from_path("input/analyses.json", sample_list=samples)
```

**Addons** let you attach optional flags or features to analyses:

```python
class QC(Enum):
    fastqc = "fastqc"
    multiqc = "multiqc"

setup_analysis_module(kind=AnalysisKind, addons={"qc": QC})
```

**Subsetting** — filter by kind or addon:

```python
wgs_analyses = analyses.subset_by_kind(AnalysisKind.wgs)
qc_analyses  = analyses.subset_by_addon(QC.fastqc)
```

---

### Decorators

#### `@cache_task` — SHA-256-based task caching

Wraps a task function so that it is only submitted when its inputs or outputs have changed. The decorator computes a SHA-256 hash from the sample's read group IDs and the task's declared outputs, then compares it against a cached hash on disk.

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

---

### Conda executors

The `Manager` automatically discovers Conda environment YAML files (`.yaml` / `.yml`) in the configured `conda_config_dir` and creates **content-addressed** environments in `conda_envs/`. A hash of the YAML content is appended to the environment name, so any change to the YAML triggers a fresh environment build while old environments remain intact.

Discovered executors are stored in a global `executor_registry` and can be referenced by YAML stem name.

---

### Registries

Two type-safe registry classes underpin the extensibility of samples, analyses, and executors:

- **`SubclassRegistry`** — ensures registered values are subclasses of a given type (used for sequencing data types and metadata/addon Enum classes).
- **`InstanceRegistry`** — ensures registered values are instances of a given type (used for executor instances).

Both raise on duplicate keys or type mismatches, catching configuration errors early.

---

## Project structure

```
input/
├── parameters.json       # Pipeline parameters
├── reference.json        # Reference file paths
├── resources.json        # Cluster resource defaults (cores, memory, walltime)
├── samples.json          # Sample definitions
├── analyses.json         # Analysis definitions
└── conda/                # Conda environment YAMLs
    ├── env_a.yaml
    └── env_b.yaml
output/                   # Persistent results
temp/                     # Intermediate files (cleaned up automatically)
workflow.py               # gwf workflow entry point
```

## License

[MIT](LICENSE)