# -*- coding: utf-8 -*-
# Copyright: (c) 2022, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ..module_utils import errors
from ..module_utils.utils import MaasValueMapper, filter_dict, is_superset

__metaclass__ = type

__metaclass__ = type


class Interface(MaasValueMapper):
    def __init__(
        # Add more values as needed.
        self,
        name=None,  # Name of Interface like eth0
        type=None,  # Type of interface, physical, bridge, bond, vlan
        id=None,  # MAAS ID of interface like 5949
        node_id=None,  # Node(Machine or Device) ID like xmkcym
        mac_address=None,  # MAC Address of interface, 90:5a:08:2f:05:58
        subnet_cidr=None,  # Subnet CIDR like 10.10.1.0/24
        subnet=None,  # Subnet Object
        vlan_id=None,  # Vlan ID like 5001
        fabric=None,  # Fabric Name
        mtu=None,  # Interface MTU, default 1500
        tags=None,  # Tags for interface, list of strings
        ip_address=None,  # IP Address V4 for interface
        default_gateway=None,  # Boolean is default gateway
        mode=None,  # Mode of interface, STATIC, Auto etc
        connected=None,  # If the interface is connected
        bond=None,  # Specific Bond Settings
        bridge=None,  # Specific Bridge Settings
        vlan_int=None,  # Speicifc Vlan interface Settings
        linked_subnets=None,  # List of linked subnets
    ):
        self.name = name
        self.type = type
        self.id = id
        self.node_id = node_id
        self.mac_address = mac_address
        self.subnet_cidr = subnet_cidr
        self.subnet = subnet
        self.vlan_id = vlan_id
        self.fabric = fabric
        self.mtu = mtu
        self.tags = tags
        self.ip_address = ip_address
        self.default_gateway = default_gateway
        self.mode = mode
        self.connected = connected
        self.bond = bond
        self.bridge = bridge
        self.vlan_int = vlan_int
        self.linked_subnets = linked_subnets

    @classmethod
    def from_ansible(cls, module):
        obj = Interface()
        obj.name = module.get("name")
        obj.type = module.get("type")
        obj.node_id = module.get("node_id")
        obj.mac_address = module.get("mac_address")
        obj.subnet_cidr = module.get("subnet_cidr")
        obj.mtu = module.get("mtu")
        obj.tags = module.get("tags", [])
        obj.ip_address = module.get("ip_address")
        obj.default_gateway = module.get("default_gateway")
        obj.mode = module.get("mode")
        obj.bond = module.get("bond")
        obj.bridge = module.get("bridge")
        obj.vlan_int = module.get("vlan_int")
        return obj

    @classmethod
    def from_maas(cls, maas_dict):
        obj = Interface()
        try:
            obj.name = maas_dict["name"]
            obj.type = maas_dict["type"]
            obj.id = maas_dict["id"]
            obj.node_id = maas_dict["system_id"]
            obj.mac_address = maas_dict["mac_address"]
            # obj.subnet_cidr = maas_dict["subnet_cidr"]
            # obj.vlan_id = maas_dict["vlan_id"]
            # obj.fabric = maas_dict["fabric"]
            obj.mtu = maas_dict["effective_mtu"]
            obj.tags = maas_dict["tags"]
            obj.connected = maas_dict.get("link_connected", False)
            obj.linked_subnets = []  # One nic can have multiple linked subnets
            for linked_subnet in maas_dict["links"] or []:
                obj.linked_subnets.append(linked_subnet)
            if maas_dict.get("discovered"):  # Auto assigned IP
                obj.ip_address = maas_dict["discovered"][0].get("ip_address")
                obj.mac_address = maas_dict["discovered"][0].get("mac_address")
                obj.subnet_cidr = maas_dict["discovered"][0]["subnet"].get("cidr")
                obj.subnet = maas_dict["discovered"][0]["subnet"]
                obj.vlan_id = maas_dict["discovered"][0]["subnet"]["vlan"].get("id")
                obj.fabric = maas_dict["discovered"][0]["subnet"]["vlan"].get("fabric")
            elif maas_dict.get("links") and len(maas_dict["links"]) > 0:  # Static IP
                obj.ip_address = maas_dict["links"][0].get("ip_address")
                obj.subnet_cidr = maas_dict["links"][0].get("subnet", {}).get("cidr")
                obj.subnet = maas_dict["links"][0].get("subnet", {})
                obj.vlan_id = (
                    maas_dict["links"][0].get("subnet", {}).get("vlan", {}).get("id")
                )
                obj.fabric = (
                    maas_dict["links"][0]
                    .get("subnet", {})
                    .get("vlan", {})
                    .get("fabric")
                )
            else:  # interface auto generated
                obj.ip_address = maas_dict.get("ip_address")
                obj.subnet_cidr = maas_dict.get("cidr")
                # "if" added because of: AttributeError: 'NoneType' object has no attribute 'get'
                if maas_dict["vlan"]:
                    obj.vlan_id = maas_dict["vlan"].get("id")
                    obj.fabric = maas_dict["vlan"].get("fabric")
        except KeyError as e:
            raise errors.MissingValueMAAS(e)
        return obj

    def to_maas(self):
        to_maas_dict = {}
        if self.id:
            to_maas_dict["id"] = self.id
        if self.name:
            to_maas_dict["name"] = self.name
        if self.mac_address:
            to_maas_dict["mac_address"] = self.mac_address
        if self.vlan_id:
            to_maas_dict["vlan"] = self.vlan_id
        if self.mtu:
            to_maas_dict["mtu"] = self.mtu
        if self.tags:
            to_maas_dict["tags"] = ",".join(self.tags)
        if self.ip_address:
            to_maas_dict["ip_address"] = self.ip_address
        if self.mode:
            to_maas_dict["mode"] = self.mode
        # FIXME: This is only set through a specific query
        # if self.default_gateway and self.mode in ["AUTO", "STATIC"]:
        #     to_maas_dict["default_gateway"] = self.default_gateway

        return to_maas_dict

    def to_ansible(self):
        return dict(
            name=self.name,
            type=self.type,
            id=self.id,
            node_id=self.node_id,
            mac_address=self.mac_address,
            subnet_cidr=self.subnet_cidr,
            mtu=self.mtu,
            tags=self.tags,
            ip_address=self.ip_address,
            mode=self.mode,
            connected=self.connected,
            bond=self.bond,
            bridge=self.bridge,
            vlan_int=self.vlan_int,
        )

    def find_linked_alias_by_cidr(self, module):
        for linked_subnet in self.linked_subnets:
            if (
                linked_subnet.get("subnet", {}).get("cidr")
                and linked_subnet["subnet"]["cidr"] == module.params["subnet_cidr"]
            ):
                return linked_subnet

    @staticmethod
    def find_subnet_by_cidr(client, cidr):
        results = client.get(
            "/api/2.0/subnets/",
        ).json
        for subnet in results:
            if subnet["cidr"] == cidr:
                return subnet
        raise ValueError(f"Subnet with {cidr} not found")

    def needs_update(self, new_nic):
        new_nic_dict = new_nic.to_maas()
        if is_superset(
            self.to_maas(),
            filter_dict(new_nic_dict, *list(new_nic_dict.keys())),
        ):
            return False
        return True

    @staticmethod
    def alias_needs_update(client, existing_alias, module):
        # Gateway can only be changed in STATIC or AUTO mode.
        # Ip_address can only be changed in STATIC mode.
        subnet = Interface.find_subnet_by_cidr(client, module.params["subnet_cidr"])
        if (
            module.params["mode"]
            and existing_alias["mode"].lower() != module.params["mode"].lower()
        ):
            return True
        if (
            module.params["mode"] == "STATIC"
            and module.params["ip_address"]
            and existing_alias.get("ip_address") != module.params["ip_address"]
        ):
            return True
        if (
            (module.params["mode"] == "STATIC" or module.params["mode"] == "AUTO")
            and module.params["default_gateway"]
            and existing_alias["gateway_ip"] != subnet["gateway_ip"]
        ):
            return True
        return False

    def send_update_request(self, client, payload):
        results = client.put(
            f"/api/2.0/nodes/{self.node_id}/interfaces/{self.id}/",
            data=payload,
        ).json
        return results

    def send_create_request(self, client, payload):
        results = client.post(
            f"/api/2.0/nodes/{self.node_id}/interfaces/",
            query={"op": f"create_{self.type.lower()}"},
            data=payload,
        ).json
        return results

    def send_delete_request(self, client):
        # DELETE does not return valid json.
        client.delete(f"/api/2.0/nodes/{self.node_id}/interfaces/{self.id}/")

    def payload_for_link_subnet(self, client):
        payload = self.to_maas()
        subnet = Interface.find_subnet_by_cidr(client, self.subnet_cidr)
        # if subnet["vlan"]["fabric"] != self.fabric:
        #     raise errors.MaasError(
        #         f"subnet - {payload['subnet_cidr']} does not have the same fabric. Try another subnet or change fabric."
        #     )
        payload["subnet"] = subnet["id"]
        return payload

    def send_link_subnet_request(self, client, payload):
        results = client.post(
            f"/api/2.0/nodes/{self.node_id}/interfaces/{self.id}/",
            query={"op": "link_subnet"},
            data=payload,
        ).json
        return results

    def send_unlink_subnet_request(self, client, linked_subnet_id):
        results = client.post(
            f"/api/2.0/nodes/{self.node_id}/interfaces/{self.id}/",
            query={"op": "unlink_subnet"},
            data={"id": linked_subnet_id},
        ).json
        return results
