#
# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
The huawei_s interfaces fact class
It is in this file the configuration is collected from the device
for a given resource, parsed, and the facts tree is populated
based on the configuration.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from copy import deepcopy
import re
from ansible.module_utils.network.common import utils
from ansible.module_utils.network.huawei_s_series.utils.utils import get_interface_type, normalize_interface
from ansible.module_utils.network.huawei_s_series.argspec.l2_interfaces.l2_interfaces import L2_InterfacesArgs


class L2_InterfacesFacts(object):
    """ The huawei_s l2 interfaces fact class
    """

    def __init__(self, module, subspec='config', options='options'):
        self._module = module
        self.argument_spec = L2_InterfacesArgs.argument_spec
        spec = deepcopy(self.argument_spec)
        if subspec:
            if options:
                facts_argument_spec = spec[subspec][options]
            else:
                facts_argument_spec = spec[subspec]
        else:
            facts_argument_spec = spec

        self.generated_spec = utils.generate_dict(facts_argument_spec)

    def populate_facts(self, connection, ansible_facts, data=None):
        """ Populate the facts for interfaces
        :param connection: the device connection
        :param ansible_facts: Facts dictionary
        :param data: previously collected conf
        :rtype: dictionary
        :returns: facts
        """
        objs = []

        if not data:
            data = connection.get('display port vlan')
        # operate on a collection of resource x
        config = data.split('\n')

        for conf in config:
            if conf:
                obj = self.render_config(self.generated_spec, conf)
                if obj:
                    objs.append(obj)
        #raise Exception(objs[3])
        facts = {}
        if objs:
            facts['l2_interfaces'] = []
            params = utils.validate_config(self.argument_spec, {'config': objs})
            for cfg in params['config']:
                facts['l2_interfaces'].append(utils.remove_empties(cfg))
        ansible_facts['ansible_network_resources'].update(facts)

        return ansible_facts

    def render_config(self, spec, conf):
        """
        Render config as dictionary structure and delete keys from spec for null values
        :param spec: The facts tree, generated from the argspec
        :param conf: The configuration
        :rtype: dictionary
        :returns: The generated config
        """
        config = deepcopy(spec)
        intf = conf.split()[0]

        if get_interface_type(intf) == 'unknown':
            return {}
        # populate the facts from the configuration
        config['name'] = normalize_interface(intf)

        if conf.split()[1] == 'access':
            access = dict()
            access['vlan'] = int(conf.split()[2])
            config['access'] = access

        if conf.split()[1] == 'trunk':
            trunk = dict()
            trunk["native_vlan"] = int(conf.split()[2])
            trunk["allowed_vlans"] = self.parse_vlan_to_list(conf.split()[3:])
            config['trunk'] = trunk

        if conf.split()[1] == 'hybrid':
            hybrid = dict()
            hybrid["native_vlan"] = int(conf.split()[2])
            hybrid["allowed_vlans"] = self.parse_vlan_to_list(conf.split()[3:])
            config['hybrid'] = hybrid

        if conf.split()[1] == 'auto':
            auto = dict()
            auto["native_vlan"] = int(conf.split()[2])
            auto["allowed_vlans"] = self.parse_vlan_to_list(conf.split()[3:])
            config['auto'] = auto

        if conf.split()[1] == 'desirable':
            desirable = dict()
            desirable["native_vlan"] = int(conf.split()[2])
            desirable["allowed_vlans"] = self.parse_vlan_to_list(conf.split()[3:])
            config['desirable'] = desirable

        return utils.remove_empties(config)

    def parse_vlan_to_list(self, vlans_lst):
        vlans_list = []
        for vlans in vlans_lst:
            vlans_list.append(vlans)
        vlans_list = sorted(set(vlans_list))
        return vlans_list