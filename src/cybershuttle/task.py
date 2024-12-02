from typing import Any

import pydantic

from .runtime import Runtime


class Task(pydantic.BaseModel):

  name: str
  app_id: str
  inputs: dict[str, Any]
  runtime: Runtime
  ref: str | None = pydantic.Field(default=None)
  agent_ref: str | None = pydantic.Field(default=None)

  @pydantic.field_validator("runtime", mode="before")
  def set_runtime(cls, v):
    if isinstance(v, dict) and "id" in v:
      id = v.pop("id")
      args = v.pop("args", {})
      return Runtime.create(id=id, args=args)
    return v

  def __str__(self) -> str:
    return f"Task(name={self.name}, app_id={self.app_id}, inputs={self.inputs}, runtime={self.runtime})"

  def launch(self) -> None:
    assert self.ref is None
    print(f"[Task] Executing {self.name} on {self.runtime}")
    self.ref = self.runtime.execute(self.name, self.app_id, self.inputs)

  def launch_agent(self) -> None:
    assert self.ref is not None
    print(f"[Task] Executing {self.name}_agent on {self.runtime}")
    self.agent_ref = self.runtime.execute(f"{self.name}_agent", "AiravataAgent", {})

  def status(self) -> str:
    assert self.ref is not None
    return self.runtime.status(self.ref)

  def files(self) -> list[str]:
    assert self.ref is not None
    return self.runtime.ls(self.ref)

  def stop(self) -> None:
    assert self.ref is not None
    return self.runtime.signal(self.ref, "SIGTERM")
