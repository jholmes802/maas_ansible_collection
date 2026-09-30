# -*- coding: utf-8 -*-
# Copyright: (c) 2022, XLAB Steampunk <steampunk@xlab.si>
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

from abc import ABC, abstractmethod

from ..module_utils import errors

__metaclass__ = type


class MaasValueMapper(ABC):
    """
    Represent abstract class.
    """

    @abstractmethod
    def to_ansible(self):
        """
        Transforms from python-native to ansible-native object.
        :return: ansible-native dictionary.
        """
        pass

    @abstractmethod
    def to_maas(self):
        """
        Transforms python-native to maas-native object.
        :return: maas-native dictionary.
        """
        pass

    @classmethod
    @abstractmethod
    def from_ansible(cls, module):
        """
        Transforms from ansible_data (module.params) to python-object.
        :param ansible_data: Field that is inputed from ansible playbook. Is most likely
        equivalent to "module.params" in python
        :return: python object
        """
        pass

    @classmethod
    @abstractmethod
    def from_maas(cls, maas_dict):
        """
        Transforms from maas-native dictionary to python-object.
        :param maas_dict: Dictionary from maas API
        :return: python object
        """
        pass

    def payload_for_create(self):
        """
        Generates the payload to run create api calls
        :return: maas-native dictionary.
        """
        return self.to_maas()

    def payload_for_update(self):
        """
        Generates the payload to run update api calls
        :return: maas-native dictionary.
        """
        return self.to_maas()

    def __eq__(self, other):
        return self.to_ansible() == other.to_ansible()


def filter_dict(input, *field_names):
    output = {}
    for field_name in field_names:
        if field_name not in input:
            continue
        value = input[field_name]
        if value is not None:
            output[field_name] = value
    return output


def is_superset(superset, subset):
    if not subset:
        return True
    for k, v in subset.items():
        if k in superset and superset[k] == v:
            continue
        return False
    return True


def filter_results(results, filter_data):
    return [element for element in results if is_superset(element, filter_data)]


def get_query(module, *field_names, ansible_maas_map):
    """
    Wrapps filter_dict and transform_ansible_to_maas_query. Prefer to use 'get_query' over filter_dict
    even if there's no mapping between maas and ansible columns for the sake of verbosity and consistency
    """
    ansible_query = filter_dict(module.params, *field_names)
    maas_query = transform_query(ansible_query, ansible_maas_map)
    return maas_query


def transform_query(raw_query, query_map):
    # Transforms query by renaming raw_query's keys by specifying those keys and the new values in query_map
    return {query_map[key]: raw_query[key] for key, value in raw_query.items()}


def is_changed(before, after):
    return not before == after


def required_one_of(module, option, list_suboptions):
    # This enables to check suboptions of an option in ansible module.
    # Fails playbook if all suboptions are missing.
    if module.params[option] is None:
        return
    module_suboptions = module.params[option].keys()
    for suboption in list_suboptions:
        if (
            suboption in module_suboptions
            and module.params[option][suboption] is not None
        ):
            return
    raise errors.MaasError(
        f"{option}: at least one of the options is required: {list_suboptions}"
    )


def clean_data(data: dict):
    return {key: value for key, value in data.items() if value is not None}


def get_match(items, key, value):
    return next((item for item in items if item.get(key) == value), None)


def must_update(old_data, new_data) -> bool:
    return any(old_data.get(key) != value for key, value in new_data.items())


def get_match_or_fail(items, key, value, attribute_name):
    result = get_match(items, key, value)
    if result:
        return result

    available_items = ", ".join(x[key] for x in items)
    raise errors.MaasError(
        f"Can not find matching {attribute_name}. Options are [{available_items}]"
    )


def get_complex_match(items, conditions: dict):
    for item in items:
        complex_conditions = {
            k: v for k, v in conditions.items() if not isinstance(k, str)
        }

        is_simple_match = all(
            item[k] == v for k, v in conditions.items() if k not in complex_conditions
        )
        is_complex_match = all(
            item[k1][k2] == v for (k1, k2), v in complex_conditions.items()
        )
        if is_simple_match and is_complex_match:
            return item

    return None
