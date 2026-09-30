# -*- coding: utf-8 -*-
# Copyright: (c) 2022, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type


from time import sleep

from ..module_utils import errors
from ..module_utils.client import Client
from ..module_utils.interface import Interface
from ..module_utils.rest_client import RestClient
from ..module_utils.utils import MaasValueMapper, get_query

ENDPOINT = "/api/2.0/nodes/"


class Node(MaasValueMapper):
    def __init__(
        # Add more values as needed.
        self,
        fqdn=None,
        hostname=None,  # Machine name.
        node_type=None,
        id=None,
        zone=None,
        domain=None,
        tags=None,
        network_interfaces=None,
    ):
        self.fqdn = fqdn
        self.hostname = hostname
        self.node_type = node_type
        self.id = id
        self.network_interfaces = network_interfaces
        self.zone = zone
        self.domain = domain
        self.tags = tags

    @classmethod
    def get_by_name(
        cls, module, client, must_exist=False, name_field_ansible="hostname"
    ):
        # Returns machine object or None
        rest_client = RestClient(client=client)
        query = get_query(
            module,
            name_field_ansible,
            ansible_maas_map={name_field_ansible: "hostname"},
        )
        maas_dict = rest_client.get_record(
            ENDPOINT,
            query,
            must_exist=must_exist,
        )
        if maas_dict:
            machine_from_maas = cls.from_maas(maas_dict)
            return machine_from_maas

    @classmethod
    def get_id_from_fqdn(cls, client, *fqdns):
        all_machines = client.get(ENDPOINT).json
        machine_list = [
            cls.from_maas(machine)
            for machine in all_machines
            if machine["fqdn"] in fqdns
        ]
        check_list = [machine.fqdn for machine in machine_list]
        for fqdn in fqdns:
            if fqdn not in check_list:
                raise errors.MaasError(f"Node - {fqdn} - not found.")
        return machine_list

    @classmethod
    def get_by_fqdn(cls, module, client, must_exist=False, name_field_ansible="fqdn"):
        # Returns machine object or None
        rest_client = RestClient(client=client)
        query = get_query(
            module,
            name_field_ansible,
            ansible_maas_map={name_field_ansible: "fqdn"},
        )
        maas_dict = rest_client.get_record(
            ENDPOINT,
            query,
            must_exist=must_exist,
        )
        if maas_dict:
            machine_from_maas = cls.from_maas(maas_dict)
            return machine_from_maas

    @classmethod
    def get_by_name_and_host(cls, module, client, must_exist=False):
        if not module.params.get("hostname") or not module.params.get("vm_host"):
            raise errors.MaasError("hostname or vm_host parameter missing.")
        maas_list = client.get(ENDPOINT).json
        for maas_dict in maas_list:
            if (
                maas_dict["hostname"] == module.params["hostname"]
                and maas_dict["pod"]["name"] == module.params["vm_host"]
            ):
                return cls.from_maas(maas_dict)
        if must_exist:
            raise errors.MachineNotFound(module.params.get("hostname"))

    @classmethod
    def get_by_id(cls, id, client):
        # rest_client.get_record doesn't work here
        # in case if machine doesn't exist .json throws error: MaasError("Received invalid JSON response: {0}".format(self.data))
        try:
            maas_dict = client.get(f"{ENDPOINT}{id}/").json
            vmhost_from_maas = cls.from_maas(maas_dict)
            return vmhost_from_maas
        except errors.MaasError:
            raise errors.MachineNotFound(id)

    @classmethod
    def get_by_tag(cls, client, tag_name):
        # Returns list of machines with the tag_name or empty list
        all_machines = client.get(ENDPOINT).json
        machine_list = [
            cls.from_maas(machine)
            for machine in all_machines
            if tag_name in machine["tag_names"]
        ]
        return machine_list

    @classmethod
    def from_ansible(cls, module):
        obj = cls()
        obj.hostname = module.params.get("hostname")
        obj.domain = module.params.get("domain")
        obj.zone = module.params.get("zone")
        obj.network_interfaces = [
            Interface.from_ansible(net_interface)
            for net_interface in module.params.get("network_interfaces") or []
        ]
        return obj

    @classmethod
    def from_maas(cls, maas_dict):
        obj = cls()
        try:
            obj.fqdn = maas_dict["fqdn"]
            obj.hostname = maas_dict["hostname"]
            obj.id = maas_dict["system_id"]
            obj.domain = maas_dict["domain"]["id"]
            obj.zone = maas_dict["zone"]["id"]
            obj.tags = maas_dict["tag_names"]
            obj.network_interfaces = [
                Interface.from_maas(net_interface)
                for net_interface in maas_dict["interface_set"] or []
            ]

        except KeyError as e:
            raise errors.MissingValueMAAS(e)
        return obj

    def to_maas(self):
        to_maas_dict = {}
        if self.hostname:
            to_maas_dict["hostname"] = self.hostname
        if self.id:
            to_maas_dict["id"] = self.id
        if self.zone:
            to_maas_dict["zone"] = self.zone
        if self.domain:
            to_maas_dict["domain"] = self.domain
        if self.network_interfaces:
            to_maas_dict["interfaces"] = [
                net_interface.to_maas() for net_interface in self.network_interfaces
            ]
        return to_maas_dict

    def to_ansible(self):
        return dict(
            fqdn=self.fqdn,
            hostname=self.hostname,
            id=self.id,
            zone=self.zone,
            tags=self.tags,
            network_interfaces=[
                net_interface.to_ansible()
                for net_interface in self.network_interfaces or []
            ],
        )

    def payload_for_compose(self, module):
        payload = self.to_maas()
        if "interfaces" in payload:
            tmp = payload.pop("interfaces")
            for net_interface in tmp:
                payload_string_list = []
                if net_interface.get("subnet_cidr"):
                    payload_string_list.append(
                        f"subnet_cidr={net_interface['subnet_cidr']}"
                    )
                if net_interface.get("ip_address"):
                    payload_string_list.append(f"ip={net_interface['ip_address']}")
                if net_interface.get("fabric"):
                    payload_string_list.append(f"fabric={net_interface['fabric']}")
                if net_interface.get("vlan"):
                    payload_string_list.append(f"vlan={net_interface['vlan']}")
                if net_interface.get("name"):
                    payload_string_list.append(f"name={net_interface['name']}")
                payload["interfaces"] = (
                    f"{net_interface['label_name']}:{','.join(payload_string_list)}"
                )
                break  # Right now, compose only allows for one network interface.
        return payload

    def find_nic_by_mac(self, mac):
        # returns nic object or None
        for nic_obj in self.network_interfaces:
            if mac == nic_obj.mac_address:
                return nic_obj

    def find_nic_by_name(self, nic_name):
        # returns nic object or None
        for nic_obj in self.network_interfaces:
            if nic_name == nic_obj.name:
                return nic_obj

    def __eq__(self, other):
        """One Node is equal to another if it has ALL attributes exactly the same"""
        return all(
            (
                self.fqdn == other.fqdn,
                self.hostname == other.hostname,
                self.id == other.id,
                self.zone == other.zone,
                self.tags == other.tags,
                self.network_interfaces == other.network_interfaces,
            )
        )

    def delete(self, client):
        client.delete(f"/api/2.0/nodes/{self.id}/")

    @classmethod
    def create(cls, client, payload):
        maas_dict = client.post("/api/2.0/nodes/", data=payload, timeout=60).json
        return cls.from_maas(maas_dict)

    def update(self, client, payload):
        return client.put(f"/api/2.0/nodes/{self.id}/", data=payload).json
