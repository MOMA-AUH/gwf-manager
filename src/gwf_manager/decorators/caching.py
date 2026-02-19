import hashlib
from functools import wraps

from ..exceptions import GwfManagerError, TaskOutputError
from ..gwf_imports import AnonymousTarget
from ..manager import Manager
from ..sample import Sample
from ..utilities import flatten


def cache_task(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        manager: Manager | None = kwargs.get("manager")
        if manager is None:
            raise GwfManagerError(
                f"'{func.__name__}' requires 'manager' as a keyword argument."
            )

        task_id_parts = [func.__name__]
        for v in kwargs.values():
            if isinstance(v, Sample):
                task_id_parts.append(v.name)
                break

        task_id = "_".join(task_id_parts)

        output_sha256_file = manager.output_file(
            "cache",
            f"{task_id}.sha256",
            mkdir=True,
        )

        # Read the cached sha256 hash, if the task has been run before
        cached_sha256_hash = None
        if output_sha256_file.exists():
            cached_sha256_hash = output_sha256_file.read_text().strip()

        # Calculate sha256 hash of all sample read groups
        sha256 = hashlib.sha256()
        for v in kwargs.values():
            if isinstance(v, Sample):
                sha256.update(v.sha256.encode("utf-8"))

        # Run the task and update the sha256 hash with its outputs
        task_outputs = func(*args, **kwargs, task_id=task_id) or {}
        if not isinstance(task_outputs, dict):
            raise TaskOutputError(
                f"Task '{task_id}' must return a dict or None, got {type(task_outputs).__name__}."
            )

        for output in sorted(flatten(task_outputs)):
            sha256.update(str(output).encode("utf-8"))

        # Join sample read group and output sha256 checksums
        sha256_hash = sha256.hexdigest()

        # If the sha256 hash of the sample read groups and task outputs is identical to the cached one,
        # do not submit the task again.
        if sha256_hash == cached_sha256_hash:
            manager.tasks[task_id].should_submit = False

        manager.submit(
            name=f"task_{task_id}",
            template=_create_task_cache_target(
                targets=manager.tasks[task_id].targets,
                sha256_hash=sha256_hash,
                sha256_file=output_sha256_file,
            ),
            task_id=None,
        )

        manager.update_task_output(
            task_id=task_id,
            paths_dict=task_outputs,
        )

        return task_outputs

    return wrapped


def _create_task_cache_target(
    targets: list[AnonymousTarget],
    sha256_hash: str,
    sha256_file: str,
) -> AnonymousTarget:
    all_target_inputs = set(flatten([target.inputs for target in targets]))
    all_target_outputs = set(flatten([target.outputs for target in targets]))

    inputs = list(all_target_inputs - all_target_outputs)
    inputs.extend(path for path in all_target_outputs if str(path).startswith("output"))

    outputs = {
        "sha256_file": sha256_file,
    }

    options = {
        "cores": 1,
        "memory": "1g",
        "walltime": "01:00:00",
    }

    spec = f"echo '{sha256_hash}' > {outputs['sha256_file']}"

    return AnonymousTarget(
        inputs=inputs,
        outputs=outputs,
        options=options,
        spec=spec,
    )
