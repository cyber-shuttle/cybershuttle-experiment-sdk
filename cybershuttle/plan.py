from __future__ import annotations

import abc
import pickle
from typing import Any


class Plan:

    tasks: list[Task] = []
    started: bool = False

    def __init__(self, inputs: dict[str, Any], tasks: list[Task]) -> None:
        for task in tasks:
            # combine with shared inputs to create the executable input set
            exec_item = {**inputs, **task.inputs}
            self.tasks.append(Task(exec_item, task.runtime))

    def describe(self) -> None:
        for task in self.tasks:
            print(task)

    def execute(self, silent: bool = False) -> None:
        if not silent:
            yesno = input("Here is the plan. Do you want to continue? (yes/no) ")
            if yesno.lower() != "yes":
                raise Exception("Execution aborted by user.")
        print("Executing plan")
        # TODO move the data to the server using the data upload APIs used by django portal
        # TODO if remote, submit jobs to the cluster
        # raise NotImplementedError()
        self.started = True

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
        with open(filename, "wb") as f:
            pickle.dump(self, f)

    def collect_results(self, runtime: Runtime) -> str:
        # TODO collect the results of the plan
        # return the file location pointer
        raise NotImplementedError()


def load(filename: str) -> Plan:
    # TODO load the plan from a file
    with open(filename, "rb") as f:
        return pickle.load(f)


class Runtime(abc.ABC):
    def __init__(self, **kwargs) -> None:
        self.args = kwargs

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
        super().__init__(**kwargs)

    def execute(self, plan: Plan):
        print("Executing Slurm job with args: ", self.args)

    @staticmethod
    def default():
        return Remote(cluster="expanse", partition="shared", profile="grprsp-1")


class Local(Runtime):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def execute(self, plan: Plan):
        print("Executing Local job with args: ", self.args)

    @staticmethod
    def default():
        return Local()


class Task:
    def __init__(self, inputs: dict[str, Any], runtime: Runtime) -> None:
        self.inputs = inputs
        self.runtime = runtime

    def __str__(self) -> str:
        return f"Task(inputs={self.inputs}, runtime={self.runtime})"

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
