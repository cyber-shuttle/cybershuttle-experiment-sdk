import abc
from typing import Any

import pydantic

from .auth import context


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


class Remote(Runtime):

  def __init__(self, **kwargs) -> None:
    super(Runtime, self).__init__(id="remote", args=kwargs)

  def upload(self, file: str) -> str:
    assert context.access_token is not None
    return ""

  def execute(self, app_id: str, inputs: dict[str, Any]) -> str:
    from .airavata import AiravataOperator

    assert context.access_token is not None
    av = AiravataOperator(context.access_token)

    # user-configured defaults
    runconf = dict(
        project_name="Default Project",
        app_name=app_id,
        experiment_name="NAMD_from_md_sdk",
        experiment_description="Testing MD-SDK for December Workshop",
        resource_host_name="login.expanse.sdsc.edu",
        group_resource_profile_name="Default",
        storage_resource_name="iguide-cybershuttle.che070035.projects.jetstream-cloud.org",
        node_count=1,
        total_cpu_count=16,
        wall_time_limit=15,
        queue_name="shared",
        gateway_id="default",
    )
    print(runconf)

    # create api server client
    assert context.access_token is not None
    auth_args = dict(
        configuration_file_location="/Users/yasith/projects/artisan/cybershuttle-experiment-sdk/settings.ini",
        username="pjaya001@odu.edu",
        password=None,
        gateway_id=runconf.get("gateway_id"),
        access_token=context.access_token,
    )
    print(auth_args)

    # define airavata sdk helpers
    av.get_accessible_apps()

    # get internal ids for the user-configured defaults
    data = dict(
        projectId=av.api_util.get_project_id(runconf.get("project_name")),
        rhId=av.api_util.get_resource_host_id(
            runconf.get("resource_host_name")),
        grpId=av.api_util.get_group_resource_profile_id(
            runconf.get("group_resource_profile_name")),
        storage=av.get_storage(str(runconf.get("storage_resource_name"))),
    )
    print(data)

    preferred_storage = av.api_util.api_server_client.get_gateway_storage_preference(
        av.api_util.token, auth_args.get("gateway_id"), data.get("storageId")
    )
    print(preferred_storage)

    # stage experiment files
    print("Copying data to compute resource: ", inputs)
    path_suffix = av.upload_files(
        host="149.165.172.192",
        port=22,
        username="exouser",
        input_path="./data",
        base_path="/home/exouser",
        project_name=runconf.get("project_name"),
        experiment_name=runconf.get("experiment_name"),
        auth_type="pkey",
    )
    assert path_suffix is not None

    print(f"Executing app_id={app_id} on Remote:", self.args)
    execution_id: str = av.launch_experiment(  # type: ignore
        experiment_name=runconf.get("experiment_name"),
        app_name=runconf.get("app_name"),
        computation_resource_name=runconf.get("resource_host_name"),
        input_path="./data",
        input_file_mapping={},
        queue_name=runconf.get("queue_name"),
        node_count=runconf.get("node_count"),
        cpu_count=runconf.get("total_cpu_count"),
        walltime=runconf.get("wall_time_limit"),
        auto_schedule=True,
    )
    print(f"Assigned exec_id={execution_id} to task")

    return execution_id

  def sidechain(self) -> str:
    raise NotImplementedError()
    from .airavata import AiravataOperator

    assert context.access_token is not None
    op = AiravataOperator(
        "/Users/yasith/projects/artisan/cybershuttle-experiment-sdk/settings.ini", context.access_token
    )

    # user-configured defaults
    runtime_config = dict(
        project_name="Default Project",
        app_name=app_id,
        experiment_name="NAMD_from_md_sdk",
        experiment_description="Testing MD-SDK for December Workshop",
        resource_host_name="login.expanse.sdsc.edu",
        group_resource_profile_name="Default",
        storage_resource_name="iguide-cybershuttle.che070035.projects.jetstream-cloud.org",
        node_count=1,
        total_cpu_count=16,
        wall_time_limit=15,
        queue_name="shared",
        gateway_id="default",
    )
    print(runtime_config)

    # create api server client
    assert context.access_token is not None
    auth_args = dict(
        configuration_file_location="/Users/yasith/projects/artisan/cybershuttle-experiment-sdk/settings.ini",
        username="pjaya001@odu.edu",
        password=None,
        gateway_id=runtime_config.get("gateway_id"),
        access_token=context.access_token,
    )
    print(auth_args)

    print(f"Launching agent on same location as app_id={
          execution_id} on Remote:")
    execution_id: str = op.launch_experiment(  # type: ignore
        experiment_name=runtime_config.get("experiment_name"),
        application_name=runtime_config.get("app_name"),
        computation_resource_name=runtime_config.get("resource_host_name"),
        local_input_path="./data",
        input_file_mapping={},
        queue_name=runtime_config.get("queue_name"),
        node_count=runtime_config.get("node_count"),
        cpu_count=runtime_config.get("total_cpu_count"),
        walltime=runtime_config.get("wall_time_limit"),
        auto_schedule=True,
    )
    print(f"Assigned exec_id={execution_id} to task")

  def status(self, ref: str) -> str:
    assert context.access_token is not None
    return "COMPLETED"

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
    return Remote(cluster="expanse", partition="shared", profile="grprsp-1")


def query(**kwargs) -> list[Runtime]:
  return [Mock.default()]
  # TODO get list using token
