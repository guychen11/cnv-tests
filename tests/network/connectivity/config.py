from tests.network.config import *  # noqa: F403

# GENERAL
IP_LINK_SHOW_BETH_CMD = 'bash -c "ip -o link show type veth | wc -l"'

# VMS
VMS = {
    "vm-fedora-1": {
        "pod_ip": None,
        "bridge_ip": "192.168.0.1",
        "bond_ip": "192.168.1.1"
    },
    "vm-fedora-2": {
        "pod_ip": None,
        "bridge_ip": "192.168.0.2",
        "bond_ip": "192.168.1.2"
    }
}
VMS_LIST = list(VMS.keys())
VM_YAML_TEMPLATE = "tests/manifests/network/vm-template-fedora-multus.yaml"

# NODES
OVS_NODES_IPS = ["192.168.0.3", "192.168.0.4"]
IP_LINK_VETH_CMD = "bash -c 'ip -o link show type veth | wc -l'"
GET_NICS_CMD = "bash -c 'ls -l /sys/class/net/ | grep -v virtual | grep net | rev | cut -d '/' -f 1 | rev'"
GET_NIC_STATE_CMD = "cat /sys/class/net/{nic}/operstate"
GET_DEFAULT_GW_CMD = "ip route show default"

# OVS
OVS_VLAN_YAML = "tests/manifests/network/ovs-vlan-net.yml"
OVS_NO_VLAN_PORT = "ovs_novlan_port"
OVS_VSCTL_ADD_BR = "ovs-vsctl add-br {bridge}"
OVS_VSCTL_ADD_PORT = "ovs-vsctl add-port {bridge} {interface}"
OVS_VSCTL_DEL_BR = "ovs-vsctl del-br {bridge}"

# LINUX BRIDGE
LINUX_BRIDGE_VLAN_YAML = "tests/manifests/network/bridge-vlan-net.yml"
LINUX_BRIDGE_BOND_YAML = "tests/manifests/network/bridge-net-bond.yml"
LINUX_BRIDGE_YAML = "tests/manifests/network/bridge-net.yml"

LINUX_BRIDGE_CREATE = "ip link add {bridge} type bridge"
LINUX_BRIDGE_ADD_IF = "ip link set dev {interface} master {bridge}"

# OVS VXLAN
OVS_BRIDGE_NAME_VXLAN = "br1_for_vxlan"
OVS_VSCTL_ADD_VXLAN = "ovs-vsctl add-port {bridge} vxlan -- set Interface vxlan type=vxlan options:remote_ip={ip}"
OVS_VSCTL_ADD_PORT_VXLAN = "ovs-vsctl add-port {bridge} {port_1} -- set Interface {port_2} type=internal"

# LINUX BRIDGE VXLAN
VXLAN_IDS = [10, 20]
VXLAN_NAME = "vxlan10"
LINUX_BRIDGE_VLAN_VXLAN = "lb_br1_vxlan"
LINUX_BRIDGE_NOVLAN_VXLAN = "lb_br2_vxlan"
LINUX_BRIDGE_CREATE_VXLAN = f"ip link add {VXLAN_NAME} type vxlan id {VXLAN_IDS.pop()} group 239.1.1.1 dstport 0 dev "
LINUX_BRIDGE_ADD_VLAN_BRIDGE_TO_VXLAN = f"ip link set {VXLAN_NAME} master {LINUX_BRIDGE_VLAN_VXLAN}"
LINUX_BRIDGE_ADD_NOVLAN_BRIDGE_TO_VXLAN = f"ip link set {VXLAN_NAME} master {LINUX_BRIDGE_NOVLAN_VXLAN}"

# BOND
BOND_SUPPORT_ENV = None
OVS_BOND_YAML = "tests/manifests/network/ovs-net-bond.yml"
BOND_NAME = "bond1"
BOND_BRIDGE = "lb_br1_bond"
IP_LINK_ADD_BOND = f"ip link add {BOND_NAME} type bond"
IP_LINK_SET_BOND_PARAMS = f"ip link set {BOND_NAME} type bond miimon 100 mode active-backup"
IP_LINK_INTERFACE_UP = "ip link set {interface} up"

# REAL NICS
REAL_NICS_ENV = None
CHECK_NIC_DRIVER_CMD = "bash -c 'basename $(readlink -f /sys/class/net/{nic}/device/driver/module/)'"
BRIDGE_NAME_REAL_NICS = "br1_real_nics"

ALL_TO_REMOVE = [
    BRIDGE_NAME_REAL_NICS, LINUX_BRIDGE_VLAN_VXLAN, LINUX_BRIDGE_NOVLAN_VXLAN, BOND_BRIDGE, VXLAN_NAME, BOND_NAME
]
