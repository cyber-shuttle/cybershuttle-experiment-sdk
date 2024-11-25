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
        from airavata_sdk.clients.sftp_file_handling_client import SFTPConnector
        from airavata_sdk.clients.utils.api_server_client_util import APIServerClientUtil
        from airavata_sdk.clients.utils.data_model_creation_util import DataModelCreationUtil
        from airavata_sdk.clients.utils.experiment_handler_util import ExperimentHandlerUtil

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

        # define airavata sdk helpers
        api_util = APIServerClientUtil(**auth_args)
        exp_util = ExperimentHandlerUtil(auth_args.get("configuration_file_location"), auth_args.get("access_token"))
        data_util = DataModelCreationUtil(**auth_args)

        # get internal ids for the user-configured defaults
        data = dict(
            projectId=api_util.get_project_id(runtime_config.get("project_name")),
            resourceHostId=api_util.get_resource_host_id(runtime_config.get("resource_host_name")),
            queue_names=exp_util.queue_names(runtime_config.get("resource_host_name")),
            groupResourceProfileId=api_util.get_group_resource_profile_id(
                runtime_config.get("group_resource_profile_name")
            ),
            storageId=api_util.get_storage_resource_id(runtime_config.get("storage_resource_name")),
        )
        print(data)

        preferred_storage = api_util.api_server_client.get_gateway_storage_preference(
            api_util.token, auth_args.get("gateway_id"), data.get("storageId")
        )
        print(preferred_storage)

        # stage experiment files
        print("Copying data to compute resource: ", inputs)
        sftp_connector = SFTPConnector(
            host="149.165.172.192",
            port=22,
            username="exouser",
            pkey="/Users/yasith/.ssh/id_rsa",
        )
        path_suffix = sftp_connector.upload_files(
            local_path="./data",
            remote_base="/home/exouser",
            project_name=runtime_config.get("project_name"),
            exprement_id=runtime_config.get("experiment_name"),
        )
        assert path_suffix is not None

        print(f"Executing app_id={app_id} on Remote:", self.args)
        experiment = data_util.get_experiment_data_model_for_single_application(
            project_name=runtime_config.get("project_name"),
            application_name=runtime_config.get("app_name"),
            experiment_name=runtime_config.get("experiment_name"),
            description=runtime_config.get("experiment_description"),
        )
        experiment = data_util.configure_computation_resource_scheduling(
            experiment_model=experiment,
            computation_resource_name=runtime_config.get("resource_host_name"),
            group_resource_profile_name=runtime_config.get("group_resource_profile_name"),
            storageId=data.get("storageId"),
            node_count=runtime_config.get("node_count"),
            total_cpu_count=runtime_config.get("total_cpu_count"),
            wall_time_limit=runtime_config.get("wall_time_limit"),
            queue_name=runtime_config.get("queue_name"),
            experiment_dir_path=path_suffix,
        )
        print(experiment.__dict__)

        execution_id = "12345"
        print(f"Assigned exec_id={execution_id} to task")

        return execution_id

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
