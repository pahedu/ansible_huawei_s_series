#
# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
The huawei_s lldp_global fact class
It is in this file the configuration is collected from the device
for a given resource, parsed, and the facts tree is populated
based on the configuration.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re
from copy import deepcopy
from ansible.module_utils.network.common import utils
from ansible.module_utils.network.huawei_s_series.argspec.lldp_global.lldp_global import Lldp_globalArgs


class Lldp_globalFacts(object):
    """ The huawei_s lldp_global fact class
    """

    def __init__(self, module, subspec='config', options='options'):
        self._module = module
        self.argument_spec = Lldp_globalArgs.argument_spec
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
        """ Populate the facts for lldp_global
        :param connection: the device connection
        :param ansible_facts: Facts dictionary
        :param data: previously collected conf
        :rtype: dictionary
        :returns: facts
        """
        objs = dict()
        if not data:
            data = connection.get('display lldp local')
        # operate on a collection of resource x
        config = data.split('\n')
        for conf in config:
            if conf:
                obj = self.render_config(self.generated_spec, conf)
                if obj:
                    objs.update(obj)
        facts = {}

        if objs:
            params = utils.validate_config(self.argument_spec, {'config': utils.remove_empties(objs)})
            facts['lldp_global'] = utils.remove_empties(params['config'])
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
        status = ''
        holdtime_multiplier = ''
        timer = ''
        reinit = ''
        match = re.search(r'LLDP Status\s+:\s*(\S+)', conf)
        if match:
            status = match.group(1)

        match = re.search(r'LLDP Message Tx Interval\s+:\s*(\d+)', conf)
        if match:
            timer = int(match.group(1))

        match = re.search(r'LLDP Message Tx Hold Multiplier\s+:\s*(\d+)', conf)
        if match:
            holdtime_multiplier = int(match.group(1))

        match = re.search(r'LLDP Refresh Delay\s+:\s*(\d+)', conf)
        if match:
            reinit = match.group(1)

        if holdtime_multiplier:
            config['holdtime_multiplier'] = int(holdtime_multiplier)
        if status:
            config['enabled'] = True
        if timer:
            config['timer'] = int(timer)
        if reinit:
            config['reinit'] = int(reinit)

        return utils.remove_empties(config)
