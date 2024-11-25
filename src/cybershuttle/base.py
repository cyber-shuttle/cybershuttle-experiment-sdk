from __future__ import annotations

import abc
from itertools import product
from typing import Any

from .plan import Plan, Runtime, Task


class GUIApp:

    name: str
    app_id: str

    def __init__(self, name: str, app_id: str) -> None:
        self.name = name
        self.app_id = app_id

    def open(self, runtime: Runtime, location: str) -> None:
        """
        Open the GUI application
        """
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def initialize(cls, **kwargs) -> GUIApp: ...


class Experiment(abc.ABC):

    application: ExperimentApp
    inputs: dict[str, Any]
    resource: Runtime = Runtime.default()
    tasks: list[Task] = []

    def __init__(self, application: ExperimentApp):
        self.application = application

    def with_inputs(self, **inputs: Any) -> Experiment:
        """
        Add shared inputs to the experiment
        """
        self.inputs = inputs
        return self

    def with_resource(self, resource: Runtime) -> Experiment:
        self.resource = resource
        return self

    def add_replica(self, runtime: Runtime | None = None) -> None:
        """
        Add a replica to the experiment.
        This will create a copy of the application with the given inputs.

        """
        self.tasks.append(
            Task(app_id=self.application.app_id, inputs={**self.inputs}, runtime=runtime or self.resource)
        )

    def add_sweep(self, runtime: Runtime | None = None, **space: list[Any]) -> None:
        """
        Add a sweep to the experiment.

        """
        for values in product(*space.values()):
            task_specific_params = dict(zip(space.keys(), values))
            self.tasks.append(
                Task(
                    app_id=self.application.app_id,
                    inputs={**self.inputs, **task_specific_params},
                    runtime=runtime or self.resource,
                )
            )

    def plan(self, **kwargs) -> Plan:
        if len(self.tasks) == 0:
            self.add_replica(self.resource)
        return Plan(
            tasks=[
                Task(app_id=self.application.app_id, inputs={**self.inputs, **t.inputs}, runtime=t.runtime)
                for t in self.tasks
            ]
        )


class ExperimentApp:

    name: str
    app_id: str

    def __init__(self, name: str, app_id: str) -> None:
        self.name = name
        self.app_id = app_id

    @classmethod
    @abc.abstractmethod
    def initialize(cls, **kwargs) -> Experiment: ...
