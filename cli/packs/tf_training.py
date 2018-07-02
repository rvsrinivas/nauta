#
# INTEL CONFIDENTIAL
# Copyright (c) 2018 Intel Corporation
#
# The source code contained or described herein and all documents related to
# the source code ("Material") are owned by Intel Corporation or its suppliers
# or licensors. Title to the Material remains with Intel Corporation or its
# suppliers and licensors. The Material contains trade secrets and proprietary
# and confidential information of Intel or its suppliers and licensors. The
# Material is protected by worldwide copyright and trade secret laws and treaty
# provisions. No part of the Material may be used, copied, reproduced, modified,
# published, uploaded, posted, transmitted, distributed, or disclosed in any way
# without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be express
# and approved by Intel in writing.
#

import ast
import yaml
import os
import re
import shutil
from typing import Tuple, List
import toml

from util.k8s import k8s_info
from util.logger import initialize_logger

import packs.common as common
from util.exceptions import KubectlIntError
import dpath.util as dutil


log = initialize_logger('packs.tf_training')


def update_configuration(experiment_folder: str, script_location: str,
                         script_folder_location: str,
                         script_parameters: Tuple[str, ...],
                         experiment_name: str,
                         internal_registry_port: str,
                         pack_type: str,
                         pack_params: List[Tuple[str, str]]):
    """
    Updates configuration of a tf-training pack based on paramaters given by a user.

    The following files are modified:
    - Dockerfile - name of a training script is replaced with the one given by a user
                 - all additional files from experiment_folder are copied into an image
                   (excluding files generated by draft)
    - charts/templates/job.yaml - list of arguments is replaces with those given by a user

    :return:
    in case of any errors it throws an exception with a description of a problem
    """
    log.debug("Update configuration - start")

    try:
        modify_values_yaml(experiment_folder, script_location, script_parameters, pack_params=pack_params,
                           experiment_name=experiment_name, pack_type=pack_type, registry_port=internal_registry_port)
        modify_dockerfile(experiment_folder, script_location, internal_registry_port)
        modify_draft_toml(experiment_folder)
    except Exception as exe:
        log.exception("Update configuration - i/o error : {}".format(exe))
        raise KubectlIntError("Configuration hasn't been updated.")

    log.debug("Update configuration - end")


def modify_dockerfile(experiment_folder: str, script_location: str, internal_registry_port: str):
    log.debug("Modify dockerfile - start")
    dockerfile_name = os.path.join(experiment_folder, "Dockerfile")
    dockerfile_temp_name = os.path.join(experiment_folder, "Dockerfile_Temp")
    dockerfile_temp_content = ""

    with open(dockerfile_name, "r") as dockerfile:
        for line in dockerfile:
            if line.startswith("ADD training.py"):
                if script_location:
                    dockerfile_temp_content = dockerfile_temp_content + common.prepare_list_of_files(experiment_folder)
            elif line.startswith("FROM dls4e/tensorflow:1.8.0-py3"):
                dockerfile_temp_content = dockerfile_temp_content + \
                                          f"FROM 127.0.0.1:{internal_registry_port}/dls4e/tensorflow:1.8.0-py3"
            else:
                dockerfile_temp_content = dockerfile_temp_content + line

    with open(dockerfile_temp_name, "w") as dockerfile_temp:
        dockerfile_temp.write(dockerfile_temp_content)

    shutil.move(dockerfile_temp_name, dockerfile_name)
    log.debug("Modify dockerfile - end")


def modify_values_yaml(experiment_folder: str, script_location: str, script_parameters: Tuple[str, ...],
                       experiment_name: str, pack_type: str, registry_port: str, pack_params: List[Tuple[str, str]]):
    log.debug("Modify values.yaml - start")
    values_yaml_filename = os.path.join(experiment_folder, f"charts/{pack_type}/values.yaml")
    values_yaml_temp_filename = os.path.join(experiment_folder, f"charts/{pack_type}/values_temp.yaml")

    with open(values_yaml_filename, "r") as values_yaml_file:
        v = yaml.load(values_yaml_file)

        if "commandline" in v:
            v["commandline"]["args"] = common.prepare_script_paramaters(script_parameters, script_location)
        v["experimentName"] = experiment_name
        v["registry_port"] = str(registry_port)

        regex = re.compile("^\[.*|^\{.*")
        for key, value in pack_params:
            if re.match(regex, value):
                try:
                    value = ast.literal_eval(value)
                except Exception as e:
                    raise AttributeError(f'Can not parse value: \"{value}\" to list/dict. Error: {e}')
            dutil.new(v, key, value, '.')

    with open(values_yaml_temp_filename, "w") as values_yaml_file:
        yaml.dump(v, values_yaml_file)

    shutil.move(values_yaml_temp_filename, values_yaml_filename)
    log.debug("Modify values.yaml - end")


def modify_draft_toml(experiment_folder: str):
    log.debug("Modify draft.toml - start")
    draft_toml_filename = os.path.join(experiment_folder, "draft.toml")
    draft_toml_temp_filename = os.path.join(experiment_folder, "draft_temp.toml")
    namespace = k8s_info.get_kubectl_current_context_namespace()

    with open(draft_toml_filename, "r") as draft_toml_file:
        t = toml.load(draft_toml_file)
        log.debug(t["environments"])
        t["environments"]["development"]["namespace"] = namespace

    with open(draft_toml_temp_filename, "w") as draft_toml_file:
        toml.dump(t, draft_toml_file)

    shutil.move(draft_toml_temp_filename, draft_toml_filename)
    log.debug("Modify draft.toml - end")
