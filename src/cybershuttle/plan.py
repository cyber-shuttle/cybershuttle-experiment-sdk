from __future__ import annotations

import abc
import json
import pydantic
from typing import Any


class Plan(pydantic.BaseModel):
    
    tasks: list[Task] = []
    started: bool = pydantic.Field(default=False, exclude=True)

    @pydantic.field_validator("tasks", mode="before")
    def default_tasks(cls, v):
        if isinstance(v, list):
            return [Task(**task) if isinstance(task, dict) else task for task in v]
        return v

    def describe(self) -> None:
        for task in self.tasks:
            print(task)

    def stage_preparation(self) -> None:
        print("Preparing execution plan...")

    def stage_confirmation(self, silent: bool) -> None:
        print("Confirming execution plan...")
        if not silent:
            while True:
                res = input("Here is the execution plan. continue? (Y/n) ")
                if res.upper() in ["N"]:
                    raise Exception("Execution was aborted by user.")
                elif res.upper() in ["Y", ""]:
                    break
                else:
                    continue

    def stage_data_movement(self) -> None:
        print("Staging data for compute resource...")
        for task in self.tasks:
            pass

    def stage_scheduling(self) -> None:
        print("Scheduling tasks on compute resource...")
        for task in self.tasks:
            pass

    def execute(self, silent: bool = False) -> None:
        try:
            self.stage_preparation()
            self.stage_confirmation(silent)
            self.stage_data_movement()
            self.stage_scheduling()
            print("Execution has started.")
            self.started = True
        except Exception as e:
            print(*e.args, sep="\n")

    def wait_for_completion(self, check_every_n_mins: int = 3) -> None:
        if not self.started:
            raise Exception("Plan has not started yet.")
        print("Waiting for completion")
        # TODO wait for the jobs to finish
        # raise NotImplementedError()

    def terminate(self) -> None:
        if not self.started:
            raise Exception("Plan has not started yet.")
        print("Terminating plan")
        # TODO terminate the jobs
        # raise NotImplementedError()
        self.started = False

    def save(self, filename: str) -> None:
        # TODO save the plan to a file
        with open(filename, "w") as f:
            json.dump(self.model_dump(), f)

    def collect_results(self, runtime: Runtime) -> str:
        # TODO collect the results of the plan
        # return the file location pointer
        raise NotImplementedError()


def load(filename: str) -> Plan:
    # TODO load the plan from a file

    with open(filename, "r") as f:
        model = json.load(f)
        return Plan(**model)


class Runtime(abc.ABC, pydantic.BaseModel):

    id: str
    args: dict[str, Any] = {}

    @abc.abstractmethod
    def execute(self, plan: Plan): ...

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(args={self.args})"

    @staticmethod
    def default():
        # return Slurm.default()
        return Remote.default()

    @staticmethod
    def Remote(**kwargs):
        return Remote(**kwargs)

    @staticmethod
    def Local(**kwargs):
        return Local(**kwargs)


class Remote(Runtime):

    def __init__(self, **kwargs) -> None:
        super(Runtime, self).__init__(id="remote", args=kwargs)

    def execute(self, plan: Plan):
        print("Executing Slurm job with args: ", self.args)

    @staticmethod
    def default():
        return Remote(cluster="expanse", partition="shared", profile="grprsp-1")


class Local(Runtime):

    def __init__(self, **kwargs) -> None:
        super(Runtime, self).__init__(id="local", args=kwargs)

    def execute(self, plan: Plan):
        print("Executing Local job with args: ", self.args)

    @staticmethod
    def default():
        return Local()


class Task(pydantic.BaseModel):

    app_id: str
    inputs: dict[str, Any]
    runtime: Runtime

    @pydantic.field_validator("runtime", mode="before")
    def set_runtime(cls, v):
        if isinstance(v, dict) and "id" in v:
            id = v.pop("id")
            args = v.pop("args", {})
            if id == "local":
                return Local(**args)
            elif id == "remote":
                return Remote(**args)
            else:
                raise ValueError(f"Unknown runtime id: {id}")
        return v

    def __str__(self) -> str:
        return f"Task(app_id={self.app_id}, inputs={self.inputs}, runtime={self.runtime})"

    def status(self) -> str:
        # TODO get the status of the job
        return "COMPLETED"
        raise NotImplementedError()

    def files(self) -> list[str]:
        # TODO get the files of the job
        return []
        raise NotImplementedError()

    def stop(self) -> None:
        # TODO stop the job
        return None
        raise NotImplementedError()
