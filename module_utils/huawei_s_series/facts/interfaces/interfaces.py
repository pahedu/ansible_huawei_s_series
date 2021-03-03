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
from ansible.module_utils.network.huawei_s_series.argspec.interfaces.interfaces import InterfacesArgs


class InterfacesFacts(object):
    """ The huawei_s interfaces fact class
    """

    def __init__(self, module, subspec='config', options='options'):
        self._module = module
        self.argument_spec = InterfacesArgs.argument_spec
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
            data = connection.get('display interface')
        # operate on a collection of resource x
        config = data.split('\n\n')
        for conf in config:
            if conf:
                obj = self.render_config(self.generated_spec, conf)
                if obj:
                    objs.append(obj)
        facts = {}

        if objs:
            facts['interfaces'] = []
            params = utils.validate_config(self.argument_spec, {'config': objs})
            for cfg in params['config']:
                facts['interfaces'].append(utils.remove_empties(cfg))
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
        match = re.search(r'^(\S+)', conf)
        if match:
            intf = match.group(1)
            if get_interface_type(intf) == 'Vlanif':
                return {}
            if get_interface_type(intf) == 'Eth-Trunk':
                return {}
            if get_interface_type(intf) == 'LoopBack':
                return {}
            if get_interface_type(intf) == 'Nve':
                return {}
            if get_interface_type(intf) == 'unknown':
                return {}
        else:
            return{}
        # populate the facts from the configuration
        config['name'] = normalize_interface(intf)

        match = re.search(r'Description\s*:\s*(.*)\nS', conf)
        if match:
            config['description'] = match.group(1)
        #config['description'] = utils.parse_conf_arg(conf, 'description')
        match = re.search(r'Speed\s*:\s*(\d+)', conf)
        if match:
            config['speed'] = match.group(1)
        #config['speed'] = utils.parse_conf_arg(conf, 'speed')
        match = re.search(r'The\s+Maximum\s+Frame\s+Length\s+is\s+(\d+)', conf)
        if match:
            config['mtu'] = match.group(1)
        #if utils.parse_conf_arg(conf, 'jumboframe enable'):
        #    config['mtu'] = int(utils.parse_conf_arg(conf, 'jumboframe enable'))
        match = re.search(r'Duplex\s*:\s*(FULL|HALF)', conf)
        if match:
            config['duplex'] = match.group(1).lower()
        #config['duplex'] = utils.parse_conf_arg(conf, 'duplex')
        match = re.search(r'Negotiation\s*:\s*(DISABLE|ENABLE)', conf)
        if match:
            if match.group(1).lower() == 'enable':
                config['negotiation'] = True
            else:
                config['negotiation'] = False
        match = re.search(r'\S+\s+current\s+state\s*:\s*(DOWN|UP|Administratively DOWN)', conf)
        if match:
            if match.group(1) == 'Administratively DOWN':
                config['enabled'] = False
            else:
                config['enabled'] = True
        #enabled = utils.parse_conf_cmd_arg(conf, 'shutdown', False)
        #config['enabled'] = enabled if enabled is not None else True

        return utils.remove_empties(config)
