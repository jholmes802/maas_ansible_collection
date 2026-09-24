# -*- coding: utf-8 -*-
# Copyright: (c) 2022, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ..module_utils import errors
from ..module_utils.client import Client
from ..module_utils.rest_client import RestClient
from ..module_utils.utils import MaasValueMapper, get_query


class RackController(MaasValueMapper):
    def __init__(
        self,
        hostname=None,
        domain=None,
        zone=None,
        system_id=None,
        resource_uri=None,
    ):
        self.hostname = hostname
        self.domain = domain
        self.zone = zone
        self.system_id = system_id
        self.resource_uri = resource_uri

    @classmethod
    def get_by_fqdn(
        cls,
        module,
        client: Client,
        must_exist=True,
        name_field_ansible="primary_rack_fqdn",
    ):
        rest_client = RestClient(client=client)
        query = get_query(
            module,
            name_field_ansible,
            ansible_maas_map={name_field_ansible: "fqdn"},
        )
        maas_dict = rest_client.get_record(
            "/api/2.0/rackcontrollers/",
            query,
            must_exist=must_exist,
        )
        if maas_dict:
            rackcontrollers_from_maas = cls.from_maas(maas_dict)
            return rackcontrollers_from_maas

    @classmethod
    def get_by_hostname(
        cls,
        module,
        client: Client,
        must_exist=True,
        name_field_ansible="hostname",
    ):
        rest_client = RestClient(client=client)
        query = get_query(
            module,
            name_field_ansible,
            ansible_maas_map={name_field_ansible: "hostname"},
        )
        maas_dict = rest_client.get_record(
            "/api/2.0/rackcontrollers/",
            query,
            must_exist=must_exist,
        )
        if maas_dict:
            rackcontrollers_from_maas = cls.from_maas(maas_dict)
            return rackcontrollers_from_maas

    @classmethod
    def from_ansible(cls, module):
        return

    @classmethod
    def from_maas(cls, maas_dict):
        obj = cls()
        try:
            obj.hostname = maas_dict["hostname"]
            obj.domain = maas_dict["domain"]
            obj.zone = maas_dict["zone"]
            obj.system_id = maas_dict["system_id"]
            obj.resource_uri = maas_dict["resource_uri"]
        except KeyError as e:
            raise errors.MissingValueMAAS(e)
        return obj

    def to_maas(self):
        return

    def to_ansible(self):
        return dict(
            hostname=self.hostname,
            domain=self.domain,
            zone=self.zone,
            system_id=self.system_id,
            resource_uri=self.resource_uri,
        )

    def delete(self, client):
        client.delete(f"/api/2.0/rackcontrollers/{self.system_id}")

    def update(self, client, payload):
        return client.put(
            f"/api/2.0/rackcontrollers/{self.system_id}",
            data=payload,
        ).json

    def __eq__(self, other):
        """One rack-controller is equal to another if it has all attributes exactly the same"""
        return all(
            (
                self.hostname == other.hostname,
                self.domain == other.domain,
                self.zone == other.zone,
                self.system_id == other.system_id,
                self.resource_uri == other.resource_uri,
            )
        )
