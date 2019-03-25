import logging

import pytest
from utilities import utils, types
from resources.node import Node
from resources.virtual_machine import VirtualMachine
from resources.virtual_machine_instance import VirtualMachineInstance
from resources.pod import Pod
from resources.resource import Resource
from autologs.autologs import generate_logs
from . import config

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope='module', autouse=True)
def prepare_env(request):
    nodes_network_info = {}
    bond_name = config.BOND_NAME
    bond_bridge = config.BOND_BRIDGE
    bridge_name_vlan_vxlan = config.LINUX_BRIDGE_VLAN_VXLAN
    bridge_name_novlan_vxlan = config.LINUX_BRIDGE_NOVLAN_VXLAN
    bridge_name_real_nics = config.BRIDGE_NAME_REAL_NICS
    vms = config.VMS_LIST
    active_node_nics = {}
    mgmt_nic = None
    ip_link_del = 'ip link del'
    ip_link_set = 'ip link set'
    vxlan_name = config.VXLAN_NAME
    resource = Resource(namespace=config.NETWORK_NS)

    def fin():
        """
        Remove test namespaces
        """
        privileged_pods = Pod().list(get_names=True, label_selector="app=privileged-test-pod")
        for pod in privileged_pods:
            pod_object = Pod(name=pod, namespace=config.NETWORK_NS)
            pod_container = pod_object.containers()[0].name
            for bridge in config.ALL_TO_REMOVE:
                pod_object.run_command(command=f"{ip_link_del} {bridge}", container=pod_container)

        for vm in vms:
            vm_object = VirtualMachine(name=vm, namespace=config.NETWORK_NS)
            if vm_object.get():
                vm_object.delete(wait=True)

        for yaml_ in (config.LINUX_BRIDGE_BOND_YAML, config.LINUX_BRIDGE_VLAN_YAML, config.LINUX_BRIDGE_YAML):
            resource.delete(yaml_file=yaml_, wait=True)

    request.addfinalizer(fin)

    for yaml_ in (config.LINUX_BRIDGE_BOND_YAML, config.LINUX_BRIDGE_VLAN_YAML, config.LINUX_BRIDGE_YAML):
        resource.create(yaml_file=yaml_, wait=True)

    compute_nodes = Node().list(get_names=True, label_selector="node-role.kubernetes.io/compute=true")
    for node in compute_nodes:
        node_obj = Node(name=node, namespace=config.NETWORK_NS)
        node_info = node_obj.get()
        for addr in node_info.status.addresses:
            if addr.type == "InternalIP":
                nodes_network_info[node] = addr.address
                break

    #  Check if we running with real NICs (not on VM)
    #  Check the number of the NICs on the node to ser BOND support
    privileged_pods = Pod().list(get_names=True, label_selector="app=privileged-test-pod")
    for idx, pod in enumerate(privileged_pods):
        pod_object = Pod(name=pod, namespace=config.NETWORK_NS)
        pod_container = pod_object.containers()[0].name
        active_node_nics[pod] = []
        err, nics = pod_object.run_command(command=config.GET_NICS_CMD, container=pod_container)
        assert err
        nics = nics.splitlines()
        err, default_gw = pod_object.run_command(command=config.GET_DEFAULT_GW_CMD, container=pod_container)
        assert err
        for nic in nics:
            err, nic_state = pod_object.run_command(
                command=config.GET_NIC_STATE_CMD.format(nic=nic), container=pod_container
            )
            assert err
            if nic_state.strip() == "up":
                if nic in [i for i in default_gw.splitlines() if 'default' in i][0]:
                    mgmt_nic = nic
                    continue

                active_node_nics[pod].append(nic)
                err, driver = pod_object.run_command(
                    command=config.CHECK_NIC_DRIVER_CMD.format(nic=nic), container=pod_container
                )
                assert err
                config.REAL_NICS_ENV = driver.strip() != "virtio_net"

        config.BOND_SUPPORT_ENV = len(active_node_nics[pod]) > 3

    #  Configure bridges on the nodes
    for idx, pod in enumerate(privileged_pods):
        pod_object = Pod(name=pod, namespace=config.NETWORK_NS)
        pod_name = pod
        pod_container = pod_object.containers()[0].name
        if config.REAL_NICS_ENV:
            interface = active_node_nics[pod_name][0]
            for cmd in (
                config.LINUX_BRIDGE_CREATE.format(bridge=bridge_name_real_nics),
                config.LINUX_BRIDGE_CREATE.format(bridge=bridge_name_novlan_vxlan),
                config.IP_LINK_INTERFACE_UP.format(interface=bridge_name_real_nics),
                config.IP_LINK_INTERFACE_UP.format(interface=bridge_name_novlan_vxlan),
                config.LINUX_BRIDGE_ADD_IF.format(interface=interface, bridge=bridge_name_real_nics),
                config.LINUX_BRIDGE_ADD_IF.format(interface=interface, bridge=bridge_name_novlan_vxlan),
                f"ip addr add {config.OVS_NODES_IPS[idx]} dev {bridge_name_novlan_vxlan}"
            ):
                assert pod_object.run_command(command=cmd, container=pod_container)[0]

        else:
            for cmd in (
                f"{config.LINUX_BRIDGE_CREATE_VXLAN} {mgmt_nic}",
                config.LINUX_BRIDGE_CREATE.format(bridge=bridge_name_vlan_vxlan),
                config.LINUX_BRIDGE_CREATE.format(bridge=bridge_name_novlan_vxlan),
                config.IP_LINK_INTERFACE_UP.format(interface=bridge_name_vlan_vxlan),
                config.IP_LINK_INTERFACE_UP.format(interface=bridge_name_novlan_vxlan),
                config.LINUX_BRIDGE_ADD_IF.format(interface=vxlan_name, bridge=bridge_name_vlan_vxlan),
                config.LINUX_BRIDGE_ADD_IF.format(interface=vxlan_name, bridge=bridge_name_novlan_vxlan),
                config.IP_LINK_INTERFACE_UP.format(interface=vxlan_name),
                f"ip addr add {config.OVS_NODES_IPS[idx]} dev {bridge_name_novlan_vxlan}"
            ):
                assert pod_object.run_command(command=cmd, container=pod_container)[0]

    #  Configure bridge on BOND if env support BOND
    if config.BOND_SUPPORT_ENV:
        for pod in privileged_pods:
            pod_object = Pod(name=pod, namespace=config.NETWORK_NS)
            pod_name = pod
            pod_container = pod_object.containers()[0].name
            for cmd in [config.IP_LINK_ADD_BOND, config.IP_LINK_SET_BOND_PARAMS]:
                assert pod_object.run_command(command=cmd, container=pod_container)[0]

            for nic in active_node_nics[pod_name][1:3]:
                for cmd in (
                    f"{ip_link_set} {nic} down",
                    f"{ip_link_set} {nic} master {bond_name}",
                    f"{ip_link_set} {nic} up"
                ):
                    assert pod_object.run_command(command=cmd, container=pod_container)[0]

            assert pod_object.run_command(command=f"{ip_link_set} {bond_name} up", container=pod_container)[0]
            res, out = pod_object.run_command(command=f"ip link show {bond_name}", container=pod_container)
            assert res
            assert "state UP" in out

            for cmd in (
                config.LINUX_BRIDGE_CREATE.format(bridge=bond_bridge),
                config.IP_LINK_INTERFACE_UP.format(interface=bond_bridge),
                config.LINUX_BRIDGE_ADD_IF.format(interface=bond_name, bridge=bond_bridge)
            ):
                assert pod_object.run_command(command=cmd, container=pod_container)[0]

    for vm in vms:
        vm_object = VirtualMachine(name=vm, namespace=config.NETWORK_NS)
        json_out = utils.get_json_from_template(
            file_=config.VM_YAML_TEMPLATE, NAME=vm, MULTUS_NETWORK="bridge-vlan-net"
        )
        spec = json_out.get('spec').get('template').get('spec')
        volumes = spec.get('volumes')
        cloud_init = [i for i in volumes if 'cloudInitNoCloud' in i][0]
        cloud_init_data = volumes.pop(volumes.index(cloud_init))
        cloud_init_user_data = cloud_init_data.get('cloudInitNoCloud').get('userData')
        cloud_init_user_data += (
            "\nruncmd:\n"
            "  - nmcli con add type ethernet con-name eth1 ifname eth1\n"
            "  - nmcli con mod eth1 ipv4.addresses {ip}/24 ipv4.method manual\n"
            "  - systemctl start qemu-guest-agent\n".format(ip=config.VMS.get(vm).get("bridge_ip"))
        )
        if not config.REAL_NICS_ENV:
            cloud_init_user_data += "  - ip link set mtu 1450 eth1\n"

        if config.BOND_SUPPORT_ENV:
            interfaces = spec.get('domain').get('devices').get('interfaces')
            networks = spec.get('networks')
            bond_bridge_interface = {'bridge': {}, 'name': 'bridge-net-bond'}
            bond_bridge_network = {'multus': {'networkName': 'bridge-net-bond'}, 'name': 'bridge-net-bond'}
            interfaces.append(bond_bridge_interface)
            networks.append(bond_bridge_network)
            cloud_init_user_data += (
                "  - nmcli con add type ethernet con-name eth1 ifname eth2\n"
                "  - nmcli con mod eth2 ipv4.addresses {ip}/24 ipv4.method manual\n".format(
                    ip=config.VMS.get(vm).get("bond_ip")
                )
            )
            spec['domain']['devices']['interfaces'] = interfaces
            spec['networks'] = networks

        cloud_init_data['cloudInitNoCloud']['userData'] = cloud_init_user_data
        volumes.append(cloud_init_data)
        spec['volumes'] = volumes
        json_out['spec']['template']['spec'] = spec
        assert vm_object.create(resource_dict=json_out, wait=True)

    for vmi in vms:
        vmi_object = VirtualMachineInstance(name=vmi, namespace=config.NETWORK_NS)
        assert vmi_object.wait_for_status(status=types.RUNNING)
        wait_for_vm_interfaces(vmi=vmi_object)
        vmi_data = vmi_object.get()
        ifcs = vmi_data.get('status', {}).get('interfaces', [])
        active_ifcs = [i.get('ipAddress') for i in ifcs if i.get('interfaceName') == "eth0"]
        config.VMS[vmi]["pod_ip"] = active_ifcs[0].split("/")[0]


@generate_logs()
def wait_for_vm_interfaces(vmi):
    """
    Wait until guest agent report VMI interfaces.

    Args:
        vmi (VirtualMachineInstance): VMI object.

    Returns:
        bool: True if agent report VMI interfaces.

    Raises:
        TimeoutExpiredError: After timeout reached.
    """
    sampler = utils.TimeoutSampler(timeout=500, sleep=1, func=vmi.get)
    for sample in sampler:
        ifcs = sample.get('status', {}).get('interfaces', [])
        active_ifcs = [i for i in ifcs if i.get('ipAddress') and i.get('interfaceName')]
        if len(active_ifcs) == len(ifcs):
            return True



