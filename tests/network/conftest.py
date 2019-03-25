# -*- coding: utf-8 -*-

"""
Pytest conftest file for CNV network tests
"""

import pytest
from tests.network import config
from resources.namespace import NameSpace
from utilities import utils, types
from resources.node import Node
from resources.pod import Pod
from resources.resource import Resource
from autologs.autologs import generate_logs


@pytest.fixture(scope="session", autouse=True)
def init(request):
    """
    Create test namespaces
    """
    resource = Resource(namespace=config.NETWORK_NS)

    def fin():
        """
        Remove test namespaces
        """
        utils.run_oc_command(command=config.SVC_DELETE_CMD)
        resource.delete(yaml_file=config.PRIVILEGED_DAEMONSET_YAML, wait=True)
        ns = NameSpace(name=config.NETWORK_NS)
        ns.delete(wait=True)
    request.addfinalizer(fin)

    ns = NameSpace(name=config.NETWORK_NS)
    assert ns.create(wait=True)
    assert ns.wait_for_status(status=types.ACTIVE)
    assert ns.work_on()
    compute_nodes = Node().list(get_names=True, label_selector="node-role.kubernetes.io/compute=true")
    assert utils.run_oc_command(command=config.SVC_CMD, namespace=config.NETWORK_NS)[0]
    assert utils.run_oc_command(command=config.ADM_CMD, namespace=config.NETWORK_NS)[0]
    assert resource.create(yaml_file=config.PRIVILEGED_DAEMONSET_YAML)
    wait_for_pods_to_match_compute_nodes_number(number_of_nodes=len(compute_nodes))
    privileged_pods = Pod().list(get_names=True, label_selector="app=privileged-test-pod")
    for idx, pod in enumerate(privileged_pods):
        pod_object = Pod(name=pod, namespace=config.NETWORK_NS)
        assert pod_object.wait_for_status(status=types.RUNNING)


@generate_logs()
def wait_for_pods_to_match_compute_nodes_number(number_of_nodes):
    """
    Wait for pods to be created from DaemonSet

    Args:
        number_of_nodes (int): Number of nodes to match for.

    Returns:
        bool: True if Pods created.

    Raises:
        TimeoutExpiredError: After timeout reached.

    """
    sampler = utils.TimeoutSampler(
        timeout=30, sleep=1, func=Pod(namespace=config.NETWORK_NS).list,
        get_names=True, label_selector="app=privileged-test-pod"
    )
    for sample in sampler:
        if len(sample) == number_of_nodes:
            return True
