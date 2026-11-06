#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2022, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: interface

author:
  - Justin Holmes (@jholmes802)
short_description: Manages network interfaces gernerically includes, physical, bonds, bridges, and vlan interfaces.
description: Connects, updates or disconnects an existing network interface machines or devices.
version_added: 1.0.0
extends_documentation_fragment:
  - maas.maas.cluster_instance
seealso: []
options:
  fqdn:
    description:
      - Fully qualified domain name of the machine or device to be deleted.
      - Serves as unique identifier of the machine or device.
      - If machine is not found the task will FAIL.
    type: str
    required: True
  type:
    description: The type of the network interface, like physical, bond, bridge, vlan.
    choices:["physical", "bond", "bridge", "vlan"]
    type: str
    default: physical
  name:
    description: Name of the network interface.
    type: str
    required: True
  state:
    description: Preferred state of the network interface.
    choices: [ present, absent ]
    type: str
    required: True
  subnet_cidr:
    description:
      - The subnet CIDR for the network interface.
      - Matches an interface attached to the specified subnet CIDR. (For example, "192.168.0.0/24".)
    type: str
    required: True
  mac_address:
    description: Valid MAC address of the network interface.
    type: str
  ip_address:
    description: Valid static IP address of the network interface.
    type: str
  bridge:
    description: Bridge Parameters only for bridge interfaces.
    type: dict
  bond:
    description: Bond Parameters only for bond interfaces.
    type: dict
  vlan_int:
    description: Vlan Parameters only for vlan interfaces.
    type: dict
  mode:
    description: Connection mode to subnet.
    choices: [ AUTO, DHCP, STATIC, LINK_UP ]
    default: AUTO
    type: str
  default_gateway:
    description: Vlan Parameters only for vlan interfaces.
    type: bool
    default: False
  tags:
    description: Valid MAC address of the network interface.
    type: list
    elements: str
"""

EXAMPLES = r"""
- name: Create subnet link on VM new-machine-3.test-domain with network interface enp5s0
  maas.maas.network_interface_link:
    cluster_instance:
      host: host-ip
      token_key: token-key
      token_secret: token-secret
      customer_key: customer-key
    machine: new-machine-3.test-domain
    state: present
    mode: STATIC
    network_interface: enp5s0
    subnet: 10.10.10.0/24
    ip_address: 10.10.10.4
    default_gateway: true
  register: nic_info

- name: Delete subnet link on VM new-machine-3.test-domain with network interface enp5s0
  maas.maas.network_interface_link:
    cluster_instance:
      host: host-ip
      token_key: token-key
      token_secret: token-secret
      customer_key: customer-key
    machine: new-machine-3.test-domain
    state: absent
    mode: STATIC
    network_interface: enp5s0
    subnet: 10.10.10.0/24
    ip_address: 10.10.10.4
    default_gateway: true
  register: nic_info
"""

RETURN = r"""
record:
  description:
    - Created or deleted subnet link.
  returned: success
  type: dict
  sample:
    id: 166
    mode: auto
    subnet:
      active_discovery: false
      allow_dns: true
      allow_proxy: true
      cidr: 10.10.10.0/24
      description: ''
      disabled_boot_architectures: []
      dns_servers: []
      gateway_ip: 10.10.10.1
      id: 2
      managed: true
      name: 10.10.10.0/24
      rdns_mode: 2
      resource_uri: /MAAS/api/2.0/subnets/2/
      space: undefined
      vlan:
        dhcp_on: true
        external_dhcp: null
        fabric: fabric-1
        fabric_id: 1
        id: 5002
        mtu: 1500
        name: untagged
        primary_rack: kwxmgm
        relay_vlan: null
        resource_uri: /MAAS/api/2.0/vlans/5002/
        secondary_rack: null
        space: undefined
        vid: 0
"""

from ansible.module_utils.basic import AnsibleModule

from ..module_utils import arguments, errors
from ..module_utils.cluster_instance import get_oauth1_client
from ..module_utils.machine import Machine
from ..module_utils.device import Device
from ..module_utils.node import Node
from ..module_utils.interface import Interface
from ..module_utils.state import NicState
from ..module_utils.utils import is_changed


def ensure_present(module, client, node_obj: Node):
    # Creates an alias not an actual physical nic.
    before = None
    after = None
    existing_nic_obj = node_obj.find_nic_by_name(module.params["name"])
    new_nic_obj = Interface.from_ansible(module.params)
    if not existing_nic_obj:
        raise errors.MaasError(
            f"Network interface with name - {module.params['name']} - not found"
        )
    existing_linked_alias = existing_nic_obj.find_linked_alias_by_cidr(module)
    if existing_linked_alias and Interface.alias_needs_update(
        client, existing_linked_alias, module
    ):
        # The only way to update alias is to delete it and make new. API endpoint is missing.
        before = existing_linked_alias
        existing_nic_obj.send_unlink_subnet_request(
            client, node_obj, existing_linked_alias["id"]
        )
        new_nic_obj.send_link_subnet_request(
            client,
            node_obj,
            new_nic_obj.payload_for_link_subnet(client, existing_nic_obj.fabric),
            existing_nic_obj.id,
        )
        updated_node_obj = Node.get_by_fqdn(
            module, client, must_exist=True, name_field_ansible="fqdn"
        )
        updated_nic_obj = updated_node_obj.find_nic_by_name(new_nic_obj.name)
        after = updated_nic_obj.find_linked_alias_by_cidr(module)
    elif not existing_linked_alias:
        new_nic_obj.id = existing_nic_obj.id
        new_nic_obj.node_id = existing_nic_obj.node_id

        try:
            new_nic_obj.send_link_subnet_request(
                client,
                new_nic_obj.payload_for_link_subnet(client),
            )
        except Exception as e:
            raise errors.MaasError(
                f"Something went wrong: {new_nic_obj.payload_for_link_subnet(client)}"
            )

        updated_node_obj = Node.get_by_fqdn(
            module, client, must_exist=True, name_field_ansible="fqdn"
        )
        updated_nic_obj = updated_node_obj.find_nic_by_name(new_nic_obj.name)
        after = updated_nic_obj.find_linked_alias_by_cidr(module)
    return is_changed(before, after), after, dict(before=before, after=after)


def ensure_absent(module, client, node_obj):
    # Deletes an alias not an actual physical nic.
    before = None
    after = None
    nic_to_delete_obj = node_obj.find_nic_by_name(module.params["name"])
    if nic_to_delete_obj:
        linked_alias_to_delete = nic_to_delete_obj.find_linked_alias_by_cidr(module)
        if linked_alias_to_delete:
            before = linked_alias_to_delete
            nic_to_delete_obj.send_unlink_subnet_request(
                client, node_obj, linked_alias_to_delete["id"]
            )
    return is_changed(before, after), after, dict(before=before, after=after)


def run(module, client):
    node_obj = Node.get_by_fqdn(
        module, client, must_exist=True, name_field_ansible="fqdn"
    )
    if module.params["state"] == NicState.present:
        changed, record, diff = ensure_present(module, client, node_obj)
    else:
        changed, record, diff = ensure_absent(module, client, node_obj)
    return changed, record, diff


def main():
    module = AnsibleModule(
        supports_check_mode=False,
        argument_spec=dict(
            arguments.get_spec("cluster_instance"),
            fqdn=dict(
                type="str",
                required=True,
            ),
            type=dict(
                type="str",
                default="physical",
                choices=[
                    "physical",
                    "bond",
                    "bridge",
                ],
            ),
            name=dict(
                type="str",
                required=True,
            ),
            state=dict(
                type="str",
                choices=["present", "absent"],
                required=True,
            ),
            subnet_cidr=dict(
                type="str",
                required=True,
            ),
            ip_address=dict(
                type="str",
            ),
            mac_address=dict(
                type="str",
            ),
            bridge=dict(
                type="dict",
            ),
            bond=dict(
                type="dict",
            ),
            vlan_int=dict(
                type="dict",
            ),
            mode=dict(
                type="str",
                choices=["AUTO", "DHCP", "STATIC", "LINK_UP"],
                default="AUTO",
            ),
            default_gateway=dict(
                type="bool",
                default=False,
            ),
        ),
    )

    try:
        client = get_oauth1_client(module.params)
        changed, record, diff = run(module, client)
        module.exit_json(changed=changed, record=record, diff=diff)
    except errors.MaasError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
