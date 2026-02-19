import attrs
from collections import defaultdict
from pathlib import Path

from .gwf_imports import AnonymousTarget, Workflow
from .path import TemporaryPath
from .utilities import legalize_for_gwf


@attrs.define
class Task:
    targets: set[AnonymousTarget] = attrs.field(factory=set)
    outputs: dict[str, str] = attrs.field(factory=dict)
    should_submit: bool = attrs.field(default=True, init=False)


class Manager:
    """Helper class to keep track of targets."""

    def __init__(self, gwf: Workflow, clean_up: bool = True) -> None:
        self.gwf = gwf
        self.clean_up = clean_up

        self.targets: dict[str, AnonymousTarget] = {}
        self.tasks: dict[str, Task] = defaultdict(Task)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.execute_workflow()

    def submit(
        self,
        name: str,
        template: AnonymousTarget,
        task_id: str | None,
    ) -> AnonymousTarget:
        """Submits a target to the internal tracking system.

        Args:
            name (str): The name of the target to be submitted.
            template (AnonymousTarget): The target template.
            task_id (str | None): The ID of the task associated with the target, if any.

        Returns:
            AnonymousTarget: The submitted target.

        Raises:
            AssertionError: If the spec of the resubmitted target with the given name differ from the spec of the previously
                            submitted target.
        """
        if name in self.targets:
            existing_template = self.targets[name]
            assert (
                existing_template.spec == template.spec
            ), f"""Differing spec of resubmitted target '{name}'{f" in task '{task_id}'" if task_id is not None else ""}"""
            template = existing_template
        else:
            self.targets[name] = template

        if task_id is not None:
            self.tasks[task_id].targets.add(template)

        return template

    def execute_workflow(self):
        """Executes the workflow by iterating over tasks and targets.

        This method performs the following steps:
        1. Iterates over all tasks and collects targets that should not be submitted.
        2. Iterates over all targets and submits those that are not in the set of targets that should not be submitted.
        """
        targets_should_submit = set()
        targets_shouldnt_submit = set()
        for task in self.tasks.values():
            if task.should_submit:
                targets_should_submit.update(task.targets)
            else:
                targets_shouldnt_submit.update(task.targets)

        # A target can be submitted in multiple tasks. Thus, we subtract all targets that should be submitted
        # from those that shouldn't.
        targets_shouldnt_submit -= targets_should_submit

        for name, target in self.targets.items():
            if target in targets_shouldnt_submit:
                continue

            self.gwf.target_from_template(
                name=legalize_for_gwf(name),
                template=_legalize_template(target),
            )

        # Optionally add a clean-up target that depends on all tasks and is executed at the end of the workflow.
        if self.clean_up:
            self.gwf.target_from_template(
                name="clean_up",
                template=_legalize_template(_create_clean_up_target(self)),
            )

    def output_dir(
        self,
        *parts: str,
        mkdir: bool = False,
    ) -> Path:
        path = Path("output", *parts)
        if mkdir:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def output_file(
        self,
        *parts: str,
        mkdir: bool = False,
    ) -> Path:
        path = Path("output", *parts)
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def temp_dir(
        self,
        *parts: str,
        mkdir: bool = False,
    ) -> TemporaryPath:
        path = TemporaryPath("temp", *parts)
        if mkdir:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def temp_file(
        self,
        *parts: str,
        mkdir: bool = False,
    ) -> TemporaryPath:
        path = TemporaryPath("temp", *parts)
        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def update_task_output(
        self,
        task_id: str,
        paths_dict: dict[str, str],
    ) -> None:
        self.tasks[task_id].outputs.update(paths_dict)

    def get_task_output(
        self,
        task_id: str,
        output_name: str,
    ) -> str:
        if task_id not in self.tasks:
            raise Exception(f"Task output {task_id} does not exist!")
        if output_name not in self.tasks[task_id].outputs:
            raise Exception(f"Output {output_name} does not exist for task {task_id}!")
        return self.tasks[task_id].outputs[output_name]


def _cast_to_str(obj):
    if isinstance(obj, dict):
        return {k: _cast_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return type(obj)(_cast_to_str(item) for item in obj)
    else:
        return str(obj)


def _legalize_template(template: AnonymousTarget) -> AnonymousTarget:
    template.inputs = _cast_to_str(template.inputs)
    template.outputs = _cast_to_str(template.outputs)
    return template


def _create_clean_up_target(manager: Manager):
    targets: list[AnonymousTarget] = []

    def _is_task_target(target: AnonymousTarget) -> bool:
        for task in manager.tasks.values():
            if target in task.targets:
                return True
        return False

    for target in manager.targets.values():
        if not _is_task_target(target):
            targets.append(target)

    inputs = []
    for target in targets:
        inputs.extend(list(target.outputs.values()))

    outputs = {
        "done_flag": manager.output_file(
            "flags",
            "done.flag",
            mkdir=True,
        ),
    }

    options = {
        "cores": 1,
        "memory": "1g",
        "walltime": "01:00:00",
    }

    spec = f"""

    rm -rf temp
    rm -rf scratch

    date > {outputs["done_flag"]}

    """

    return AnonymousTarget(
        inputs=inputs,
        outputs=outputs,
        options=options,
        spec=spec,
    )
