from __future__ import annotations

import abc
from itertools import product
from typing import Any, Generic, TypeVar

from .plan import Plan
from .runtime import Runtime
from .task import Task


class GUIApp:

  app_id: str

  def __init__(self, app_id: str) -> None:
    self.app_id = app_id

  def open(self, runtime: Runtime, location: str) -> None:
    """
    Open the GUI application
    """
    raise NotImplementedError()

  @classmethod
  @abc.abstractmethod
  def initialize(cls, **kwargs) -> GUIApp: ...


class ExperimentApp:

  app_id: str

  def __init__(self, app_id: str) -> None:
    self.app_id = app_id

  @classmethod
  @abc.abstractmethod
  def initialize(cls, **kwargs) -> Experiment: ...


T = TypeVar("T", ExperimentApp, GUIApp)


class Experiment(Generic[T], abc.ABC):

  name: str
  application: T
  inputs: dict[str, Any]
  input_mapping: dict[str, str]
  resource: Runtime = Runtime.default()
  tasks: list[Task] = []

  def __init__(self, name: str, application: T):
    self.name = name
    self.application = application
    self.input_mapping = {}

  def with_inputs(self, **inputs: Any) -> Experiment[T]:
    """
    Add shared inputs to the experiment
    """
    self.inputs = inputs
    return self

  def with_resource(self, resource: Runtime) -> Experiment[T]:
    self.resource = resource
    return self

  def add_replica(self, *allowed_runtimes: Runtime) -> None:
    """
    Add a replica to the experiment.
    This will create a copy of the application with the given inputs.

    """
    # TODO random scheduling for now
    import random
    runtime = random.choice(allowed_runtimes) if len(allowed_runtimes) > 0 else self.resource

    self.tasks.append(
        Task(
            name=self.name,
            app_id=self.application.app_id,
            inputs={**self.inputs},
            runtime=runtime,
        )
    )

  def add_sweep(self, runtime: Runtime | None = None, **space: list[Any]) -> None:
    """
    Add a sweep to the experiment.

    """
    for values in product(*space.values()):
      task_specific_params = dict(zip(space.keys(), values))
      agg_inputs = {**self.inputs, **task_specific_params}
      task_inputs = {k: agg_inputs[v] for k, v in self.input_mapping.items()}
      self.tasks.append(Task(
          name=self.name,
          app_id=self.application.app_id,
          inputs=task_inputs,
          runtime=runtime or self.resource,
      ))

  def plan(self, **kwargs) -> Plan:
    if len(self.tasks) == 0:
      self.add_replica(self.resource)
    tasks = []
    for t in self.tasks:
      agg_inputs = {**self.inputs, **t.inputs}
      task_inputs = {k: agg_inputs[v] for k, v in self.input_mapping.items()}
      tasks.append(Task(name=t.name, app_id=self.application.app_id, inputs=task_inputs, runtime=t.runtime))
    return Plan(tasks=tasks)
