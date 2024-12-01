import abc
from typing import Any

import pydantic

from .auth import context


class Runtime(abc.ABC, pydantic.BaseModel):

  id: str
  args: dict[str, str | int | float] = pydantic.Field(default={})

  @abc.abstractmethod
  def upload(self, file: str) -> str: ...

  @abc.abstractmethod
  def execute(
      self,
      experiment_name: str,
      app_id: str,
      inputs: dict[str, Any],
  ) -> str: ...

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
    # return Mock()
    return Remote.default()

  @staticmethod
  def create(id: str, args: dict[str, Any]) -> "Runtime":
    if id == "mock":
      return Mock(**args)
    elif id == "remote":
      return Remote(**args)
    else:
      raise ValueError(f"Unknown runtime id: {id}")

  @staticmethod
  def Remote(**kwargs):
    return Remote(**kwargs)

  @staticmethod
  def Local(**kwargs):
    return Mock(**kwargs)


class Mock(Runtime):

  _state: int = 0

  def __init__(self) -> None:
    super(Runtime, self).__init__(id="mock")

  def upload(self, file: str) -> str:
    return ""

  def execute(
      self,
      experiment_name: str,
      app_id: str,
      inputs: dict[str, Any],
  ) -> str:
    import uuid
    print(f"[Mock] experiment_name={experiment_name}")
    print(f"[Mock] copying data={inputs}")
    print(f"[Mock] running experiment: \nname={experiment_name} \napp_id={app_id} \nargs={self.args}")
    execution_id = str(uuid.uuid4())
    print(f"[Mock] returning exec_id={execution_id}")
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


class Remote(Runtime):

  def __init__(self, **kwargs) -> None:
    super(Runtime, self).__init__(id="remote", args=kwargs)

  def upload(self, file: str) -> str:
    assert context.access_token is not None
    return ""

  def execute(
      self,
      experiment_name: str,
      app_id: str,
      inputs: dict[str, Any],
  ) -> str:
    assert context.access_token is not None
    from .airavata import AiravataOperator
    av = AiravataOperator(context.access_token)

    print(f"[Remote] experiment_name={experiment_name}, av={av}")

    assert "cluster" in self.args

    ex_id = av.launch_experiment(
        experiment_name=experiment_name,
        app_name=app_id,
        computation_resource_name=str(self.args["cluster"]),
        inputs=inputs
    )
    print("experiment_id:", ex_id)
    return ex_id

  def status(self, ref: str) -> str:
    assert context.access_token is not None
    from .airavata import AiravataOperator
    av = AiravataOperator(context.access_token)

    status = av.get_experiment_status(ref)
    print("status={status}")
    return status # type: ignore

  def signal(self, ref: str, signal: str) -> None:
    assert context.access_token is not None
    pass

  def ls(self, ref: str) -> list[str]:
    assert context.access_token is not None
    return []

  def download(self, ref: str, file: str) -> str:
    assert context.access_token is not None
    return ""

  @staticmethod
  def default():
    return Remote(
        cluster="login.expanse.sdsc.edu",
    )


def query(**kwargs) -> list[Runtime]:
  return [Mock.default(), Remote.default()]
  # TODO get list using token
