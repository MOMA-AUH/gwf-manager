import os
from functools import wraps

from ..gwf_imports import AnonymousTarget
from ..utilities import flatten


def use_wd_scratch(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        template: AnonymousTarget = func(*args, **kwargs)
        return _augment_spec_with_scratch(
            template,
            scratch_path=f"scratch/{func.__name__}/${{SLURM_JOB_ID}}",
        )

    return wrapped


def use_custom_scratch(scratch_path: str):
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            template: AnonymousTarget = func(*args, **kwargs)
            return _augment_spec_with_scratch(template, scratch_path)

        return wrapped

    return decorator


def _augment_spec_with_scratch(
    template: AnonymousTarget,
    scratch_path: str,
) -> AnonymousTarget:
    flat_inputs = flatten(template.inputs)
    flat_outputs = flatten(template.outputs)

    mkdir_in_cmds, symlink_cmds = set(), set()
    for p in flat_inputs:
        if os.path.isabs(p):
            continue
        mkdir_in_cmds.add(f"mkdir -p {os.path.dirname(p)}")
        symlink_cmds.add(f"ln -s ${{GWF_EXEC_WORKFLOW_ROOT}}/{p} {p}")

    mkdir_out_cmds, mv_cmds = set(), set()
    for p in flat_outputs:
        if os.path.isabs(p):
            continue
        mkdir_out_cmds.add(f"mkdir -p {os.path.dirname(p)}")
        mv_cmds.add(f"mv ${{SCRATCH_DIR}}/{p} {p}")

    template.spec = f"""

# Create scratch directory
SCRATCH_DIR="{scratch_path}"
mkdir -p ${{SCRATCH_DIR}}

# Change to scratch directory
cd ${{SCRATCH_DIR}}

# Create input directories in scratch and symlink inputs
{"\n".join(sorted(mkdir_in_cmds))}
{"\n".join(sorted(symlink_cmds))}

# Create output directories in scratch
{"\n".join(sorted(mkdir_out_cmds))}

{template.spec.strip()}

# Add sync to ensure all files are written to disk
sync

# Change to working directory
cd ${{GWF_EXEC_WORKFLOW_ROOT}}

# Create output directories
{"\n".join(sorted(mkdir_out_cmds))}

# Move outputs from scratch to final location
{"\n".join(sorted(mv_cmds))}

# Clean up scratch
rm -rf ${{SCRATCH_DIR}}

    """.strip()

    return template
