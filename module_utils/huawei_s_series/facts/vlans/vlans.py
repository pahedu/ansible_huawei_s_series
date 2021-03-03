#
# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
The huaiwe_s vlans fact class
It is in this file the configuration is collected from the device
for a given resource, parsed, and the facts tree is populated
based on the configuration.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type


from copy import deepcopy
from ansible.module_utils.network.common import utils
from ansible.module_utils.network.huawei_s_series.argspec.vlans.vlans import VlansArgs


class VlansFacts(object):
    """ The huaiwe_s vlans fact class
    """

    def __init__(self, module, subspec='config', options='options'):
        self._module = module
        self.argument_spec = VlansArgs.argument_spec
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
        """ Populate the facts for vlans
        :param connection: the device connection
        :param ansible_facts: Facts dictionary
        :param data: previously collected conf
        :rtype: dictionary
        :returns: facts
        """
        if connection:
            pass

        objs = []
        final_objs = []
        if not data:
            data = connection.get('display vlan')
        # operate on a collection of resource x
        config = data.split('\n')
        # Get individual vlan configs separately
        vlan_info = ''
        for conf in config:
            if 'Description' in conf:
                vlan_info = 'Name'
            if conf and ' ' not in filter(None, conf.split('-')):
                obj = self.render_config(self.generated_spec, conf, vlan_info)
                if obj:
                    objs.append(obj)

        facts = {}
        facts['vlans'] = []
        params = utils.validate_config(self.argument_spec, {'config': objs})

        for cfg in params['config']:
            facts['vlans'].append(utils.remove_empties(cfg))
        ansible_facts['ansible_network_resources'].update(facts)

        return ansible_facts

    def render_config(self, spec, conf, vlan_info):
        """
        Render config as dictionary structure and delete keys
          from spec for null values

        :param spec: The facts tree, generated from the argspec
        :param conf: The configuration
        :rtype: dictionary
        :returns: The generated config
        """
        config = deepcopy(spec)

        if conf == '--------------------------------------------------------------------------------':
            pass
        else:
            if vlan_info == 'Name' and 'Description' not in conf:
                conf = list(filter(None, conf.split(' ')))
                config['vlan_id'] = int(conf[0])
                config['name'] = conf[5]
                if conf[1] == 'enable':
                    config['state'] = 'active'
                config['shutdown'] = 'disabled'

        return utils.remove_empties(config)
