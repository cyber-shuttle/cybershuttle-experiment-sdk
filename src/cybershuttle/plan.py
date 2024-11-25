from __future__ import annotations

import abc
import json
import time
from typing import Any

import pydantic


class Plan(pydantic.BaseModel):

    tasks: list[Task] = []

    @pydantic.field_validator("tasks", mode="before")
    def default_tasks(cls, v):
        if isinstance(v, list):
            return [Task(**task) if isinstance(task, dict) else task for task in v]
        return v

    def describe(self) -> None:
        for task in self.tasks:
            print(task)

    def __stage_prepare__(self) -> None:
        print("Preparing execution plan...")
        self.describe()

    def __stage_confirm__(self, silent: bool) -> None:
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

    def __stage_begin__(self) -> None:
        print("Starting tasks...")
        for task in self.tasks:
            task.begin()

    def __stage_status__(self) -> list[str]:
        print("Checking task(s) status...")
        statuses = []
        for task in self.tasks:
            statuses.append(task.status())
        print("task(s) status:", statuses)
        return statuses

    def __stage_stop__(self) -> None:
        print("Stopping task(s)...")
        for task in self.tasks:
            task.stop()
        print("Task(s) stopped.")

    def run(self, silent: bool = False) -> None:
        try:
            self.__stage_prepare__()
            self.__stage_confirm__(silent)
            self.__stage_begin__()
        except Exception as e:
            print(*e.args, sep="\n")

    def join(self, check_every_n_mins: float = 0.1) -> None:
        while True:
            statuses = self.__stage_status__()
            if all(status == "COMPLETED" for status in statuses):
                print("Task(s) complete.")
                break
            sleep_time = check_every_n_mins * 60
            print(f"Task(s) running. rechecking in {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)

    def stop(self) -> None:
        self.__stage_stop__()

    def save_json(self, filename: str) -> None:
        with open(filename, "w") as f:
            json.dump(self.model_dump(), f)

    @staticmethod
    def load_json(filename: str) -> Plan:
        with open(filename, "r") as f:
            model = json.load(f)
            return Plan(**model)

    def collect_results(self, runtime: Runtime) -> str:
        # TODO collect the results of the plan
        # return the file location pointer
        raise NotImplementedError()


class Runtime(abc.ABC, pydantic.BaseModel):

    id: str
    args: dict[str, Any] = pydantic.Field(default={})

    @abc.abstractmethod
    def upload(self, file: str) -> str: ...

    @abc.abstractmethod
    def execute(self, app_id: str, inputs: dict[str, Any]) -> str: ...

    @abc.abstractmethod
    def status(self, ref: str) -> str: ...

    @abc.abstractmethod
    def signal(self, ref: str, signal: str) -> None: ...

    @abc.abstractmethod
    def ls(self, ref: str) -> list[str]: ...

    @abc.abstractmethod
    def download(self, ref: str, file: str) -> str: ...

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
        return Mock(**kwargs)


class Remote(Runtime):

    def __init__(self, **kwargs) -> None:
        super(Runtime, self).__init__(id="remote", args=kwargs)

    def upload(self, file: str) -> str:
        return ""

    def execute(self, app_id: str, inputs: dict[str, Any]) -> str:
        print("Copying data to compute resource: ", inputs)
        print(f"Executing app_id={app_id} on Remote:", self.args)
        execution_id = "12345"
        print(f"Assigned exec_id={execution_id} to task")
        return execution_id

    def status(self, ref: str) -> str:
        return "COMPLETED"

    def signal(self, ref: str, signal: str) -> None:
        pass

    def ls(self, ref: str) -> list[str]:
        return []

    def download(self, ref: str, file: str) -> str:
        return ""

    @staticmethod
    def default():
        return Mock()
        # return Remote(cluster="expanse", partition="shared", profile="grprsp-1")


class Mock(Runtime):

    _state: int = 0

    def __init__(self) -> None:
        super(Runtime, self).__init__(id="mock")

    def upload(self, file: str) -> str:
        return ""

    def execute(self, app_id: str, inputs: dict[str, Any]) -> str:
        import uuid

        print("Copying data to compute resource: ", inputs)
        print(f"Executing app_id={app_id} on Mock:", self.args)
        execution_id = str(uuid.uuid4())
        print(f"Assigned exec_id={execution_id} to task")
        return execution_id

    def status(self, ref: str) -> str:
        import random

        self._state += random.randint(0, 5)
        if self._state > 10:
            return "COMPLETED"
        return "RUNNING"

    def signal(self, ref: str, signal: str) -> None:
        pass

    def ls(self, ref: str) -> list[str]:
        return []

    def download(self, ref: str, file: str) -> str:
        return ""

    @staticmethod
    def default():
        return Mock()


class Task(pydantic.BaseModel):

    app_id: str
    inputs: dict[str, Any]
    runtime: Runtime
    ref: str | None = pydantic.Field(default=None, exclude=True)

    @pydantic.field_validator("runtime", mode="before")
    def set_runtime(cls, v):
        if isinstance(v, dict) and "id" in v:
            id = v.pop("id")
            args = v.pop("args", {})
            if id == "mock":
                return Mock(**args)
            elif id == "remote":
                return Remote(**args)
            else:
                raise ValueError(f"Unknown runtime id: {id}")
        return v

    def __str__(self) -> str:
        return f"Task(app_id={self.app_id}, inputs={self.inputs}, runtime={self.runtime})"

    def begin(self) -> None:
        app_id = self.app_id
        inputs = self.inputs
        runtime = self.runtime
        ref = runtime.execute(app_id, inputs)
        self.ref = ref

    def status(self) -> str:
        assert self.ref is not None
        return self.runtime.status(self.ref)

    def files(self) -> list[str]:
        assert self.ref is not None
        return self.runtime.ls(self.ref)

    def stop(self) -> None:
        assert self.ref is not None
        return self.runtime.signal(self.ref, "SIGTERM")
