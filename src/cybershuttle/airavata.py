import configparser
import logging
import os
from typing import Literal

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

    def __init__(self, configuration_file_location: str, access_token: str):
        self.configuration_file_location = configuration_file_location
        self.access_token = access_token

        self.api_server_client = APIServerClient(self.configuration_file_location)
        self.gateway_conf = GatewaySettings(self.configuration_file_location)
        self.experiment_conf = ExperimentSettings(self.configuration_file_location)

        self.airavata_token = self.__airavata_token__(self.access_token, self.gateway_conf.GATEWAY_ID)
        self.api_util = APIServerClientUtil(
            configuration_file_location,
            username=self.user_id,
            password="",
            gateway_id=self.gateway_conf.GATEWAY_ID,
            access_token=self.access_token,
        )

    def __airavata_token__(self, access_token, gateway_id):
        decode = jwt.decode(access_token, options={"verify_signature": False})
        self.user_id = decode["preferred_username"]
        claimsMap = {"userName": self.user_id, "gatewayID": gateway_id}

        return AuthzToken(accessToken=self.access_token, claimsMap=claimsMap)

    def get_experiment(self, experiment_id):
        return self.api_server_client.get_experiment(self.airavata_token, experiment_id)

    def get_application_list(self):
        modules = self.api_server_client.get_all_app_modules(self.airavata_token, self.gateway_conf.GATEWAY_ID)
        return modules

    def get_compatible_deployments(self, application_module_id):
        api_util = APIServerClientUtil(
            self.configuration_file_location, self.user_id, "", self.gateway_conf.GATEWAY_ID, self.access_token
        )
        grp_id = api_util.get_group_resource_profile_id(self.experiment_conf.GROUP_RESOURCE_PROFILE_NAME)
        deployments = self.api_server_client.get_application_deployments_for_app_module_and_group_resource_profile(
            self.airavata_token, application_module_id, grp_id
        )

        return deployments

    def get_compute_resources(self, resource_ids):
        resources = []
        for resource_id in resource_ids:
            resources.append(self.api_server_client.get_compute_resource(self.airavata_token, resource_id))

        return resources

    def get_group_resource_profile_id(self, group_resource_profile_name):
        response = self.api_server_client.get_group_resource_list(self.airavata_token, self.gateway_conf.GATEWAY_ID)
        for x in list(response):  # type: ignore
            if x.groupResourceProfileName == group_resource_profile_name:
                return x.groupResourceProfileId
        return None

    def upload_files(
        self,
        host,
        port,
        username,
        local_input_path,
        base_path,
        project_name,
        experiment_name,
        auth_type: Literal["token", "pkey"],
    ):
        if auth_type == "token":
            sftp_connector = SFTPConnector(host=host, port=port, username=username, password=self.access_token)
        elif auth_type == "pkey":
            sftp_connector = SFTPConnector(host=host, port=port, username=username, pkey="/Users/yasith/.ssh/id_rsa")
        else:
            raise ValueError("Invalid auth_type")
        return sftp_connector.upload_files(local_input_path, base_path, project_name, experiment_name)

    def launch_experiment(
        self,
        experiment_name,
        application_name,
        computation_resource_name,
        local_input_path,
        input_file_mapping={},
        queue_name=None,
        node_count=None,
        cpu_count=None,
        walltime=None,
        auto_schedule=False,
    ):
        data_model_util = DataModelCreationUtil(
            self.configuration_file_location,
            username=self.user_id,
            password=None,
            gateway_id=self.gateway_conf.GATEWAY_ID,
            access_token=self.access_token,
        )

        grp_id = self.api_util.get_group_resource_profile_id(self.experiment_conf.GROUP_RESOURCE_PROFILE_NAME)
        app_id = self.api_util.get_execution_id(application_name)
        storage_id = self.api_util.get_storage_resource_id(self.experiment_conf.STORAGE_RESOURCE_HOST)
        resource_host_id = self.api_util.get_resource_host_id(computation_resource_name)

        experiment = data_model_util.get_experiment_data_model_for_single_application(
            project_name=self.experiment_conf.PROJECT_NAME,
            application_name=application_name,
            experiment_name=experiment_name,
            description=experiment_name,
        )

        path_suffix = self.upload_files(
            self.experiment_conf.STORAGE_RESOURCE_HOST,
            self.experiment_conf.SFTP_PORT,
            self.user_id,
            "",
            local_input_path,
            self.experiment_conf.PROJECT_NAME,
            experiment.experimentName,
            auth_type="token",
        )

        logger.info("Input files uploaded to %s", path_suffix)

        path = self.gateway_conf.GATEWAY_DATA_STORE_DIR + path_suffix

        queue_name = queue_name if queue_name is not None else self.experiment_conf.QUEUE_NAME

        node_count = node_count if node_count is not None else self.experiment_conf.NODE_COUNT

        cpu_count = cpu_count if cpu_count is not None else self.experiment_conf.TOTAL_CPU_COUNT

        walltime = walltime if walltime is not None else self.experiment_conf.WALL_TIME_LIMIT

        logger.info("configuring inputs ......")
        experiment = data_model_util.configure_computation_resource_scheduling(
            experiment_model=experiment,
            computation_resource_name=computation_resource_name,
            group_resource_profile_name=self.experiment_conf.GROUP_RESOURCE_PROFILE_NAME,
            storageId=storage_id,
            node_count=int(node_count),
            total_cpu_count=int(cpu_count),
            wall_time_limit=int(walltime),
            queue_name=queue_name,
            experiment_dir_path=path,
            auto_schedule=auto_schedule,
        )

        input_files = []
        if len(input_file_mapping.keys()) > 0:
            new_file_mapping = {}
            for key in input_file_mapping.keys():
                if type(input_file_mapping[key]) == list:
                    data_uris = []
                    for x in input_file_mapping[key]:
                        data_uri = data_model_util.register_input_file(
                            file_identifier=x,
                            storage_name=self.experiment_conf.STORAGE_RESOURCE_HOST,
                            storageId=storage_id,
                            input_file_name=x,
                            uploaded_storage_path=path,
                        )
                        data_uris.append(data_uri)
                    new_file_mapping[key] = data_uris
                else:
                    x = input_file_mapping[key]
                    data_uri = data_model_util.register_input_file(
                        file_identifier=x,
                        storage_name=self.experiment_conf.STORAGE_RESOURCE_HOST,
                        storageId=storage_id,
                        input_file_name=x,
                        uploaded_storage_path=path,
                    )
                    new_file_mapping[key] = data_uri
            experiment = data_model_util.configure_input_and_outputs(
                experiment, input_files=None, application_name=application_name, file_mapping=new_file_mapping
            )

            print(new_file_mapping)
        else:
            for x in os.listdir(local_input_path):
                if (
                    x == "inputs.ini"
                ):  # Ignore command line inputs file. In future, read all input file locations from this one
                    continue
                if os.path.isfile(local_input_path + "/" + x):
                    input_files.append(x)

            if len(input_files) > 0:
                data_uris = []
                for x in input_files:
                    data_uri = data_model_util.register_input_file(
                        file_identifier=x,
                        storage_name=self.experiment_conf.STORAGE_RESOURCE_HOST,
                        storageId=storage_id,
                        input_file_name=x,
                        uploaded_storage_path=path,
                    )
                    data_uris.append(data_uri)
                experiment = data_model_util.configure_input_and_outputs(
                    experiment, input_files=data_uris, application_name=application_name
                )
            else:
                inputs = self.api_server_client.get_application_inputs(self.airavata_token, app_id)
                experiment.experimentInputs = inputs

        outputs = self.api_server_client.get_application_outputs(self.airavata_token, app_id)

        experiment.experimentOutputs = outputs

        ## Setting up command line inputs

        exp_inputs: list = experiment.experimentInputs  # type: ignore
        if not exp_inputs:
            exp_inputs = []

        execution_id = self.api_util.get_execution_id(application_name)
        all_inputs = self.api_server_client.get_application_inputs(self.airavata_token, execution_id)

        config = configparser.ConfigParser()
        config.read(local_input_path + "/inputs.ini")

        inputs_to_replace = []

        if application_name in config:
            for input in all_inputs:  # type: ignore
                for input_name in list(config[application_name].keys()):
                    if input.name.lower() == input_name and input.type < 3:  ## Command line input types
                        input.value = config[application_name][input_name]
                        inputs_to_replace.append(input)

        for input in inputs_to_replace:
            found = False
            for exp_in in exp_inputs:  # type: ignore
                if exp_in.name == input.name:
                    exp_in.value = input.value
                    found = True
                    continue
            if not found:
                exp_inputs.append(input)

        experiment.experimentInputs = exp_inputs

        # create experiment
        ex_id = self.api_server_client.create_experiment(self.airavata_token, self.gateway_conf.GATEWAY_ID, experiment)

        # launch experiment
        self.api_server_client.launch_experiment(self.airavata_token, ex_id, self.gateway_conf.GATEWAY_ID)

        return ex_id
        # if not grp_id:

    def get_experiment_status(self, experiment_id):
        status = self.api_server_client.get_experiment_status(self.airavata_token, experiment_id)
        return status
