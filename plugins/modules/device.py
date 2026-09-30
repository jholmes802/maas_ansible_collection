#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2022, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: device

author:
  - Justin Holmes 
short_description: Provides a resource to manage MAAS devices.
description:
  - If I(state) is C(present) and I(name) is not provided or not found, adds an existing device to the system.
  - If I(state) is C(present) and I(name) is found, updates an existing device in the system.
  - If I(state) is C(absent) selected device is deleted.
version_added: 1.0.0
extends_documentation_fragment:
  - maas.maas.cluster_instance
seealso: []
options:
  state:
    description:
      - Desired state of the machine.
    choices: [ present, absent ]
    type: str
    required: True
  fqdn:
    description:
      - Fully qualified domain name of the machine to be updated or deleted.
      - Serves as unique identifier of the machine.
      - If machine is not found the task will FAIL.
    type: str
  hostname:
    description:
      - Name of the device to be added. In case of updating the device, this parameter is used for updating the name of the device .
      - In case if new device  is added, the name is computed if it's not set.
    type: str
    required: true
  zone:
    description:
      - The zone of the machine.
      - This is computed if it's not set.
    type: str
  domain:
    description:
      - The domain of the device.
      - This is computed if it's not set.
    type: str
  description:
    description:
      - The description of the device.
      - This is computed if it's not set.
    type: str
  parent:
    description:
      - The ID parent of the device.
    type: str
  tags:
    description:
      - The tags of the device.
    type: str
  mac_address:
    description:
      - The primary MAC Address of the device.
      - This is only used during creating the device, 
    type: str
    required: true
"""

# TODO: Update This
EXAMPLES = r"""
- name: Add Device to the system
  maas.maas.device:
    state: present
    fqdn: new-device.maas
    hostname: new-device
    domain: maas
    mac_address: 00:00:00:00:00:00


- name: Update existing machine
  maas.maas.machine:
    state: present
    fqdn: new-machine.maas
    power_type: virsh
    power_parameters:
      power_address: ...
      power_pass: ...
      power_id: ...
    architecture: i386/generic
    name: updated-machine
    domain: new-domain
    pool: new-pool
    zone: new-zone
    min_hwe_kernel: ga-20.04

- name: Delete machine
  maas.maas.machine:
    state: absent
    fqdn: my-machine
"""

# TODO: Update This
RETURN = r"""
record:
  description:
    - Added machine.
  returned: success
  type: dict
  sample:
    architecture: amd64/generic
    cores: 2
    distro_series: focal
    fqdn: new-machine.maas
    name: new-machine
    hwe_kernel: hwe-22.04
    id: 6h4fn6
    memory: 2048
    min_hwe_kernel: ga-22.04
    network_interfaces:
    - fabric: fabric-1
      id: 277
      ip_address: 10.10.10.190
      mac_address: 00:00:00:00:00:01
      name: my-net
      subnet_cidr: 10.10.10.0/24
      vlan: untagged
    osystem: ubuntu
    pool: default
    power_type: lxd
    status: Commissioning
    storage_disks:
    - id: 288
      name: sda
      size_gigabytes: 3
    - id: 289
      name: sdb
      size_gigabytes: 5
    tags:
      - pod-console-logging
      - my-tag
    zone: default
"""


import json

from ansible.module_utils.basic import AnsibleModule

from ..module_utils import arguments, errors
from ..module_utils.client import Client
from ..module_utils.cluster_instance import get_oauth1_client
from ..module_utils.device import Device
from ..module_utils.utils import clean_data, get_match, must_update


def ensure_present(module, client: Client):
    # extract all data from ansible task
    fqdn = module.params["fqdn"]

    changed: bool = False
    before = {}
    item_from_ansible = Device.from_ansible(module)

    # find a match on server, if none, create new object
    item_from_maas = Device.get_by_fqdn(module, client)
    if not item_from_maas:
        response_json = item_from_ansible.create(client)
        item_from_maas = response_json  # Set this so update check below can handle any missing things
        changed = True

    # Set ID
    id = item_from_maas.id

    # check if update is needed at all
    item_changed = item_from_ansible == item_from_maas

    # update object
    if item_changed:
        response_json = item_from_mass.update(client)
        before = item_from_maas.to_ansible()
    else:
        response_json = item_from_maas

    return (
        changed,
        item_from_maas.to_ansible(),
        dict(before=before, after=response_json.to_ansible()),
    )


def ensure_absent(module, client: Client):
    fqdn = module.params["fqdn"]

    items = client.get(ENDPOINT).json
    item = get_match(items, "fqdn", fqdn)
    if not item:
        return False, None, dict(before={}, after={})

    id = item.get("id")
    client.delete(f"{ENDPOINT}/{id}/")
    return True, None, dict(before=item, after={})


def run(module, client: Client):
    if not module.params["fqdn"]:
        module.params["fqdn"] = (
            module.params["hostname"] + "." + module.params["domain"]
        )
    if module.params["state"] == "present":
        record, changed, diff = ensure_present(module, client)
    elif module.params["state"] == "absent":
        record, changed, diff = ensure_absent(module, client)
    return changed, record, diff


def main():
    module = AnsibleModule(
        supports_check_mode=True,
        argument_spec=dict(
            arguments.get_spec("cluster_instance"),
            state=dict(
                type="str",
                choices=["present", "absent"],
                required=True,
            ),
            fqdn=dict(type="str"),
            hostname=dict(type="str"),
            zone=dict(type="str"),
            domain=dict(type="str", default="maas"),
            description=dict(type="str"),
            parent=dict(type="str"),
            tags=dict(type="str"),
            mac_address=dict(type="str"),
        ),
        required_if=[
            ("state", "absent", ("fqdn",), False),
        ],
    )

    try:
        client = get_oauth1_client(module.params)
        changed, record, diff = run(module, client)
        module.exit_json(changed=changed, record=record, diff=diff)
    except errors.MaasError as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
