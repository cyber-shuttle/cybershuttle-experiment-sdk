from __future__ import annotations

import json
import time

import pydantic

from .runtime import Runtime
from .task import Task


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

    def __stage_fetch__(self) -> list[list[str]]:
        print("Fetching results...")
        fps = list[list[str]]()
        for task in self.tasks:
            runtime = task.runtime
            ref = task.ref
            fps_task = list[str]()
            assert ref is not None
            for remote_fp in task.files():
                fp = runtime.download(ref, remote_fp)
                fps_task.append(fp)
            fps.append(fps_task)
        print("Results fetched.")
        return fps

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

    def collect_results(self, runtime: Runtime) -> list[list[str]]:
        return self.__stage_fetch__()
