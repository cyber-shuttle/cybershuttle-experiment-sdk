import configparser
import logging
import os
from pathlib import Path

import jwt
from airavata.model.security.ttypes import AuthzToken
from airavata_sdk.clients.api_server_client import APIServerClient
from airavata_sdk.clients.sftp_file_handling_client import SFTPConnector
from airavata_sdk.clients.utils.api_server_client_util import APIServerClientUtil
from airavata_sdk.clients.utils.data_model_creation_util import DataModelCreationUtil
from airavata_sdk.transport.settings import ExperimentSettings, GatewaySettings

logger = logging.getLogger("airavata_sdk.clients")
logger.setLevel(logging.INFO)


class AiravataOperator:

  def __init__(self, access_token: str, config_file: str = "settings.ini"):
    # store variables
    self.config_file = config_file
    self.access_token = access_token
    # load api server settings and create client
    self.api_server_client = APIServerClient(self.config_file)
    # load gateway settings
    self.gateway_conf = GatewaySettings(self.config_file)
    gateway_id = self.gateway_conf.GATEWAY_ID
    # load experiment settings
    self.experiment_conf = ExperimentSettings(self.config_file)
    self.airavata_token = self.__airavata_token__(self.access_token, gateway_id)
    self.api_util = APIServerClientUtil(self.config_file, username=self.user_id, password="", gateway_id=gateway_id, access_token=self.access_token)

  def __airavata_token__(self, access_token, gateway_id):
    """
    Decode access token (string) and create AuthzToken (object)

    """
    decode = jwt.decode(access_token, options={"verify_signature": False})
    self.user_id = str(decode["preferred_username"])
    claimsMap = {"userName": self.user_id, "gatewayID": gateway_id}
    return AuthzToken(accessToken=self.access_token, claimsMap=claimsMap)

  def get_experiment(self, experiment_id: str):
    """
    Get experiment by id

    """
    return self.api_server_client.get_experiment(self.airavata_token, experiment_id)

  def get_accessible_apps(self, gateway_id: str | None = None):
    """
    Get all applications available in the gateway

    """
    # use defaults for missing values
    gateway_id = gateway_id or self.gateway_conf.GATEWAY_ID
    # logic
    app_interfaces = self.api_server_client.get_all_application_interfaces(self.airavata_token, gateway_id)
    return app_interfaces

  def get_preferred_storage(self, gateway_id: str | None = None, storage_name: str | None = None):
    """
    Get preferred storage resource

    """
    # use defaults for missing values
    gateway_id = gateway_id or self.gateway_conf.GATEWAY_ID
    storage_name = storage_name or self.experiment_conf.STORAGE_RESOURCE_HOST
    # logic
    storage_id = self.api_util.get_storage_resource_id(storage_name)
    return self.api_server_client.get_gateway_storage_preference(self.airavata_token, gateway_id, storage_id)

  def get_storage(self, storage_name: str | None = None) -> any:  # type: ignore
    """
    Get storage resource by name

    """
    # use defaults for missing values
    storage_name = storage_name or self.experiment_conf.STORAGE_RESOURCE_HOST
    # logic
    storage_id = self.api_util.get_storage_resource_id(storage_name)
    storage = self.api_util.api_server_client.get_storage_resource(self.airavata_token, storage_id)
    return storage

  def get_group_resource_profile(self, grp_name: str | None = None):
    """
    Get group resource profile by name

    """
    # use defaults for missing values
    grp_name = grp_name or self.experiment_conf.GROUP_RESOURCE_PROFILE_NAME
    # logic
    grp_id = self.api_util.get_group_resource_profile_id(grp_name)
    grp = self.api_util.api_server_client.get_group_resource_profile(self.airavata_token, grp_id)
    return grp

  def get_compatible_deployments(self, app_interface_id: str, grp_name: str | None = None):
    """
    Get compatible deployments for an application interface and group resource profile

    """
    # use defaults for missing values
    grp_name = grp_name or self.experiment_conf.GROUP_RESOURCE_PROFILE_NAME
    # logic
    grp_id = self.api_util.get_group_resource_profile_id(grp_name)
    deployments = self.api_server_client.get_application_deployments_for_app_module_and_group_resource_profile(self.airavata_token, app_interface_id, grp_id)
    return deployments

  def get_app_interface_id(self, app_name: str, gateway_id: str | None = None):
    """
    Get application interface id by name

    """
    self.api_util.gateway_id = str(gateway_id or self.gateway_conf.GATEWAY_ID)
    return self.api_util.get_execution_id(app_name)

  def get_application_inputs(self, app_interface_id: str) -> list:
    """
    Get application inputs by id

    """
    return list(self.api_server_client.get_application_inputs(self.airavata_token, app_interface_id))  # type: ignore

  def get_compute_resources_by_ids(self, resource_ids: list[str]):
    """
    Get compute resources by ids

    """
    return [self.api_server_client.get_compute_resource(self.airavata_token, resource_id) for resource_id in resource_ids]

  def upload_files(self, storage_resource, input_path: str, project_name: str, experiment_name: str) -> str:
    """
    Upload input files to storage resource, and return the remote path

    Return Path: /{project_name}/{experiment_name}

    """
    host = storage_resource.hostName
    port = self.experiment_conf.SFTP_PORT
    sftp_connector = SFTPConnector(host=host, port=port, username=self.user_id, password=self.access_token)
    upload_path = sftp_connector.upload_files(input_path, project_name, experiment_name)
    logger.info("Input files uploaded to %s", upload_path)
    return upload_path

  def launch_experiment(
      self,
      experiment_name: str,
      app_name: str,
      computation_resource_name: str,
      input_path: str,
      input_mapping: dict = {},
      *,
      gateway_id: str | None = None,
      queue_name: str | None = None,
      grp_name: str | None = None,
      sr_host: str | None = None,
      project_name: str | None = None,
      node_count: int | None = None,
      cpu_count: int | None = None,
      walltime: int | None = None,
      auto_schedule: bool = False,
  ):
    """
    Launch an experiment

    """
    # preprocess args (str)
    gateway_id = str(gateway_id or self.gateway_conf.GATEWAY_ID)
    queue_name = str(queue_name or self.experiment_conf.QUEUE_NAME)
    grp_name = str(grp_name or self.experiment_conf.GROUP_RESOURCE_PROFILE_NAME)
    sr_host = str(sr_host or self.experiment_conf.STORAGE_RESOURCE_HOST)
    project_name = str(project_name or self.experiment_conf.PROJECT_NAME)
    mount_point = Path(self.gateway_conf.GATEWAY_DATA_STORE_DIR) / self.user_id

    # preprocess args (int)
    node_count = int(node_count or self.experiment_conf.NODE_COUNT or "1")
    cpu_count = int(cpu_count or self.experiment_conf.TOTAL_CPU_COUNT or "1")
    walltime = int(walltime or self.experiment_conf.WALL_TIME_LIMIT or "30")

    # validate args (str)
    assert len(experiment_name) > 0
    assert len(app_name) > 0
    assert len(computation_resource_name) > 0
    assert len(input_path) > 0
    assert len(input_mapping) >= 0
    assert len(gateway_id) > 0
    assert len(queue_name) > 0
    assert len(grp_name) > 0
    assert len(sr_host) > 0
    assert len(project_name) > 0
    assert len(mount_point.as_posix()) > 0

    # validate args (int)
    assert node_count > 0
    assert cpu_count > 0
    assert walltime > 0

    # upload data files (SFTP)
    storage = self.get_storage(sr_host)
    upload_path = self.upload_files(
        storage_resource=storage,
        input_path=input_path,
        project_name=project_name,
        experiment_name=experiment_name,
    )
    # upload_path remains the same across gateways, only the mount_point would change
    abs_path = mount_point / upload_path

    # setup runtime params
    queue_name = queue_name or self.experiment_conf.QUEUE_NAME
    node_count = int(node_count or self.experiment_conf.NODE_COUNT or "1")
    cpu_count = int(cpu_count or self.experiment_conf.TOTAL_CPU_COUNT or "1")
    walltime = int(walltime or self.experiment_conf.WALL_TIME_LIMIT or "01:00:00")
    sr_id = storage.storageResourceId

    # setup application interface
    app_interface_id = self.get_app_interface_id(app_name)
    assert app_interface_id is not None

    # create experiment
    data_model_util = DataModelCreationUtil(
        self.config_file,
        username=self.user_id,
        password=None,
        gateway_id=gateway_id,
        access_token=self.access_token,
    )
    experiment = data_model_util.get_experiment_data_model_for_single_application(
        experiment_name=experiment_name,
        application_name=app_name,
        project_name=project_name,
        description=experiment_name,
    )
    experiment = data_model_util.configure_computation_resource_scheduling(
        experiment_model=experiment,
        computation_resource_name=computation_resource_name,
        group_resource_profile_name=grp_name,
        storageId=sr_id,
        node_count=node_count,
        total_cpu_count=cpu_count,
        wall_time_limit=walltime,
        queue_name=queue_name,
        experiment_dir_path=abs_path.as_posix(),
        auto_schedule=auto_schedule,
    )

    # setup experiment inputs
    config = configparser.ConfigParser()
    config.read(os.path.join(input_path, 'inputs.ini'))

    def register_input(fp):
      return data_model_util.register_input_file(fp, sr_host, sr_id, fp, abs_path.as_posix())

    input_files = [
        register_input(file.as_posix()) for file in Path(input_path).iterdir()
        if file.is_file() and file.name != 'inputs.ini'
    ] if not input_mapping else []

    file_mapping = {
        key: [register_input(x) for x in value] if isinstance(value, list) else register_input(value)
        for key, value in input_mapping.items()
    } if input_mapping else {}

    print(input_files)
    print(file_mapping)

    experiment = data_model_util.configure_input_and_outputs(
        experiment_model=experiment,
        application_name=app_name,
        input_files=input_files,
        file_mapping=file_mapping,
    )

    if app_name in config:
      for exp_input in experiment.experimentInputs:
        if exp_input.type < 3:
          exp_input.value = config[app_name].get(exp_input.name.lower(), exp_input.value)

    # setup experiment outputs
    outputs = self.api_server_client.get_application_outputs(self.airavata_token, app_interface_id)
    experiment.experimentOutputs = outputs

    # create experiment
    ex_id = self.api_server_client.create_experiment(self.airavata_token, self.gateway_conf.GATEWAY_ID, experiment)

    # launch experiment
    self.api_server_client.launch_experiment(self.airavata_token, ex_id, self.gateway_conf.GATEWAY_ID)

    return ex_id

  def get_experiment_status(self, experiment_id):
    status = self.api_server_client.get_experiment_status(
        self.airavata_token, experiment_id)
    return status
