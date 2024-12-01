from typing import Any

import pydantic

from .runtime import Runtime


class Task(pydantic.BaseModel):

  name: str
  app_id: str
  inputs: dict[str, Any]
  runtime: Runtime
  ref: str | None = pydantic.Field(default=None, exclude=True)

  @pydantic.field_validator("runtime", mode="before")
  def set_runtime(cls, v):
    if isinstance(v, dict) and "id" in v:
      id = v.pop("id")
      args = v.pop("args", {})
      return Runtime.create(id=id, args=args)
    return v

  def __str__(self) -> str:
    return f"Task(name={self.name}, app_id={self.app_id}, inputs={self.inputs}, runtime={self.runtime})"

  def begin(self) -> None:
    app_id = self.app_id
    inputs = self.inputs
    runtime = self.runtime
    print(f"Executing task: {self.name} on {runtime}")
    ref = runtime.execute(self.name, app_id, inputs)
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
