#
# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
The huawei_s_lag_interfaces class
It is in this file where the current configuration (as dict)
is compared to the provided configuration (as dict) and the command set
necessary to bring the current configuration to it's desired end-state is
created
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type


import re
from ansible.module_utils.network.common import utils
from ansible.module_utils.network.common.cfg.base import ConfigBase
from ansible.module_utils.network.common.utils import to_list
from ansible.module_utils.network.huawei_s_series.facts.facts import Facts
from ansible.module_utils.network.huawei_s_series.utils.utils import dict_to_set
from ansible.module_utils.network.huawei_s_series.utils.utils import filter_dict_having_none_value, remove_duplicate_interface


class Lag_interfaces(ConfigBase):
    """
    The huawei_s_lag_interfaces class
    """

    gather_subset = [
        '!all',
        '!min',
    ]

    gather_network_resources = [
        'lag_interfaces',
    ]

    def __init__(self, module):
        super(Lag_interfaces, self).__init__(module)

    def get_lag_interfaces_facts(self):
        """ Get the 'facts' (the current configuration)

        :rtype: A dictionary
        :returns: The current configuration as a dictionary
        """
        facts, _warnings = Facts(self._module).get_facts(self.gather_subset, self.gather_network_resources)
        lag_interfaces_facts = facts['ansible_network_resources'].get('lag_interfaces')
        if not lag_interfaces_facts:
            return []
        return lag_interfaces_facts

    def execute_module(self):
        """ Execute the module

        :rtype: A dictionary
        :returns: The result from module execution
        """
        result = {'changed': False}
        commands = list()
        warnings = list()

        existing_lag_interfaces_facts = self.get_lag_interfaces_facts()
        commands.extend(self.set_config(existing_lag_interfaces_facts))

        if commands:
            if not self._module.check_mode:
                self._connection.edit_config(commands)
            result['changed'] = True
        result['commands'] = commands

        changed_lag_interfaces_facts = self.get_lag_interfaces_facts()

        result['before'] = existing_lag_interfaces_facts
        if result['changed']:
            result['after'] = changed_lag_interfaces_facts

        result['warnings'] = warnings
        return result

    def set_config(self, existing_lag_interfaces_facts):
        """ Collect the configuration from the args passed to the module,
            collect the current configuration (as a dict from facts)

        :rtype: A list
        :returns: the commands necessary to migrate the current configuration
                  to the desired configuration
        """
        want = self._module.params['config']
        have = existing_lag_interfaces_facts
        resp = self.set_state(want, have)
        return to_list(resp)

    def set_state(self, want, have):
        """ Select the appropriate function based on the state provided

        :param want: the desired configuration as a dictionary
        :param have: the current configuration as a dictionary
        :rtype: A list
        :returns: the commands necessary to migrate the current configuration
                  to the desired configuration
        """

        state = self._module.params['state']
        if state in ('overridden', 'merged', 'replaced') and not want:
            self._module.fail_json(msg='value of config parameter must not be empty for state {0}'.format(state))

        module = self._module
        if state == 'overridden':
            commands = self._state_overridden(want, have, module)
        elif state == 'deleted':
            commands = self._state_deleted(want, have)
        elif state == 'merged':
            commands = self._state_merged(want, have, module)
        elif state == 'replaced':
            commands = self._state_replaced(want, have, module)
        return commands

    def _state_replaced(self, want, have, module):
        """ The command generator when state is replaced

        :rtype: A list
        :returns: the commands necessary to migrate the current configuration
                  to the desired configuration
        """
        commands = []

        for interface in want:
            for each in have:
                if each['name'] == interface['name']:
                    break
            else:
                continue
            commands.extend(self._clear_config(interface, each))
            commands.extend(self._set_config(interface, each, module))
        # Remove the duplicate interface call
        commands = commands

        return commands

    def _state_overridden(self, want, have, module):
        """ The command generator when state is overridden

        :rtype: A list
        :returns: the commands necessary to migrate the current configuration
                  to the desired configuration
        """
        commands = []

        for each in have:
            for interface in want:
                if each['name'] == interface['name']:
                    break
            else:
                # We didn't find a matching desired state, which means we can
                # pretend we recieved an empty desired state.
                interface = dict(name=each['name'])
                kwargs = {'want': interface, 'have': each}
                commands.extend(self._clear_config(**kwargs))
                continue
            commands.extend(self._clear_config(dict(), each))
            commands.extend(self._set_config(interface, each, module))

        # Remove the duplicate interface call
        commands = commands

        return commands

    def _state_merged(self, want, have, module):
        """ The command generator when state is merged

        :rtype: A list
        :returns: the commands necessary to merge the provided into
                  the current configuration
        """
        commands = []

        for interface in want:
            for each in have:
                if each.get('name') == interface.get('name'):
                    break
                else:
                    continue
            commands.extend(self._set_config(interface, each, module))

        return commands

    def _state_deleted(self, want, have):
        """ The command generator when state is deleted

        :rtype: A list
        :returns: the commands necessary to remove the current configuration
                  of the provided objects
        """
        commands = []

        if want:
            for interface in want:
                for each in have:
                    if each.get('name') == interface['name']:
                        break
                else:
                    continue
                commands.extend(self._clear_config(interface, each))
        else:
            for each in have:
                commands.extend(self._clear_config(dict(), each))

        return commands

    def remove_command_from_config_list(self, interface, cmd, commands):
        # To delete the passed config
        if interface not in commands:
            commands.append(interface)
        commands.append('undo %s' % cmd)
        return commands

    def add_command_to_config_list(self, interface, cmd, commands):
        # To set the passed config
        if interface not in commands:
            commands.append(interface)
        commands.append(cmd)
        return commands

    def _set_config(self, want, have, module):
        # Set the interface config based on the want and have config
        commands = []

        #Sort values in want and have dict
        if want.get('members'):
            j = 0
            for intr in want['members']:
                intr = dict(sorted(intr.items()))
                want['members'][j] = intr
                j += 1
        if have.get('members'):
            j = 0
            for intr in have['members']:
                intr = dict(sorted(intr.items()))
                have['members'][j] = intr
                j += 1

        # To remove keys with None values from want dict
        want = utils.remove_empties(want)
        # Get the diff b/w want and have
        want_dict = dict_to_set(want)
        have_dict = dict_to_set(have)
        diff = want_dict - have_dict
        if diff:
            diff = dict(diff)
            interface = 'interface {0}'.format(want.get('name'))

            for each in diff['members']:
                each = dict(each)
                if each.get('mode') == 'active' or each.get('mode') == 'passive':
                    cmd = 'mode lacp'
                    self.add_command_to_config_list(interface, cmd, commands)
                if each.get('mode') == 'on':
                    cmd = 'mode manual load-balance'
                    self.add_command_to_config_list(interface, cmd, commands)
                cmd = 'trunkport {0}'.format(each.get('member'))
                self.add_command_to_config_list(interface, cmd, commands)

        if commands:
            self.add_command_to_config_list(interface, 'quit', commands)

        return commands

    def _clear_config(self, want, have):
        # Delete the interface config based on the want and have config
        commands = []
        want_interface = []
        have_interface = []

        if want.get('name'):
            interface = 'interface ' + want['name']
        else:
            interface = 'interface ' + have['name']

        if have.get('members') and want.get('members') is None:
            for each in have.get('members'):
                cmd = 'trunkport {0}'.format(each.get('member'))
                self.remove_command_from_config_list(interface, cmd, commands)
                cmd = 'mode'
                self.remove_command_from_config_list(interface, cmd, commands)
        elif have.get('members') and want.get('members'):
            for each in have.get('members'):
                have_interface.append(each.get('member'))
                for every in want.get('members'):
                    want_interface.append(every.get('member'))
                    if each.get('member') == every.get('member'):
                        if each.get('mode') != every.get('mode'):
                            cmd = 'mode'
                            self.remove_command_from_config_list(interface, cmd, commands)
            have_interface = set(have_interface)
            want_interface = set(want_interface)
            diff_interface = have_interface - want_interface
            for each_int in diff_interface:
                cmd = 'trunkport {0}'.format(each_int)
                self.remove_command_from_config_list(interface, cmd, commands)

        if commands:
            self.add_command_to_config_list(interface, 'quit', commands)

        return commands
