#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2017, Ansible by Red Hat, inc
#
# This file is part of Ansible by Red Hat
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = """
---
module: huawei_s_static_route
version_added: "2.9"
author: "Aleksandr Natov (@pahedu)"
short_description: Manage static IP routes on Huawei S Series network devices
description:
  - This module provides declarative management of static
    IP routes on Huawei S Series network devices.
notes:
  - Tested against VRP V200R010C00SPC600
options:
  prefix:
    description:
      - Network prefix of the static route.
  mask:
    description:
      - Network prefix mask of the static route.
  next_hop:
    description:
      - Next hop IP of the static route.
  vrf:
    description:
      - VRF of the static route.
  interface:
    description:
      - Interface of the static route.
  name:
    description:
      - Name of the static route
    aliases: ['description']
  admin_distance:
    description:
      - Admin distance of the static route.
  tag:
    description:
      - Set tag of the static route.
  track:
    description:
      - Tracked item to depend on for the static route.
  aggregate:
    description: List of static route definitions.
  state:
    description:
      - State of the static route configuration.
    default: present
    choices: ['present', 'absent']
extends_documentation_fragment: huawei_s
"""

EXAMPLES = """
- name: configure static route
  huawei_s_static_route:
    prefix: 192.168.2.0
    mask: 255.255.255.0
    next_hop: 10.0.0.1

- name: configure black hole in vrf blue depending on nqa item test
  huawei_s_static_route:
    prefix: 192.168.2.0
    mask: 255.255.255.0
    vrf: blue
    interface: null0
    track: test test 

- name: configure ultimate route with name and tag
  huawei_s_static_route:
    prefix: 192.168.2.0
    mask: 255.255.255.0
    interface: Vlanif1
    name: route_description
    tag: 100

- name: remove configuration
  huawei_s_static_route:
    prefix: 192.168.2.0
    mask: 255.255.255.0
    next_hop: 10.0.0.1
    state: absent

- name: Add static route aggregates
  huwei_s_static_route:
    aggregate:
      - { prefix: 172.16.32.0, mask: 255.255.255.0, next_hop: 10.0.0.8 }
      - { prefix: 172.16.33.0, mask: 255.255.255.0, next_hop: 10.0.0.8 }

- name: Remove static route aggregates
  huawei_s_static_route:
    aggregate:
      - { prefix: 172.16.32.0, mask: 255.255.255.0, next_hop: 10.0.0.8 }
      - { prefix: 172.16.33.0, mask: 255.255.255.0, next_hop: 10.0.0.8 }
    state: absent
"""

RETURN = """
commands:
  description: The list of configuration mode commands to send to the device
  returned: always
  type: list
  sample:
    - ip route-static 192.168.2.0 255.255.255.0 10.0.0.1
"""
from copy import deepcopy
import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.common.utils import remove_default_spec, validate_ip_address
from ansible.module_utils.network.huawei_s_series.huawei_s import get_config, load_config
from ansible.module_utils.network.huawei_s_series.huawei_s import huawei_s_argument_spec, check_args


def map_obj_to_commands(want, have):
    commands = list()

    for w in want:
        state = w['state']
        del w['state']
        # Try to match an existing config with the desired config
        for h in have:
            # To delete admin_distance param from have if not it want before comparing both fields
            if not w.get('admin_distance') and h.get('admin_distance'):
                del h['admin_distance']
            diff = list(set(w.items()) ^ set(h.items()))
            if not diff:
                break
            # if route is present with name or name already starts with wanted name it will not change
            elif len(diff) == 2 and diff[0][0] == diff[1][0] == 'name' and (not w['name'] or h['name'].startswith(w['name'])):
                break
        # If no matches found, clear `h`
        else:
            h = None

        command = 'ip route-static'
        prefix = w['prefix']
        mask = w['mask']
        vrf = w.get('vrf')
        if vrf:
            command = ' '.join((command, 'vpn-instance', vrf, prefix, mask))
        else:
            command = ' '.join((command, prefix, mask))

        for key in ['interface', 'next_hop', 'admin_distance', 'tag', 'track', 'name']:
            if w.get(key):
                if key == 'name' and len(w.get(key).split()) > 1:
                    command = ' '.join((command, 'description', '"%s"' % w.get(key)))  # name with multiple words needs to be quoted
                elif key == 'interface':
                    command = ' '.join((command, w.get(key)))
                elif key == 'next_hop':
                    command = ' '.join((command, w.get(key)))
                elif key == 'name':
                    command = ' '.join((command, 'description', w.get(key)))
                elif key == 'tag':
                    command = ' '.join((command, 'tag', w.get(key)))
                elif key == 'track':
                    command = ' '.join((command, 'track nqa', w.get(key)))
                elif key == 'admin_distance':
                    command = ' '.join((command, 'preference', w.get(key)))

        if state == 'absent' and h:
            command = 'undo ip route-static'
            prefix = w['prefix']
            mask = w['mask']
            vrf = w.get('vrf')
            intr = w.get('interface')
            next_hop = w.get('next_hop')
            if vrf:
                command = ' '.join((command, 'vpn-instance', vrf, prefix, mask))
            else:
                command = ' '.join((command, prefix, mask))
            if intr:
                command = ' '.join((command, intr))
            if next_hop:
                command = ' '.join((command, next_hop))
            commands.append(command)
        elif state == 'present' and not h:
            commands.append(command)

    return commands


def map_config_to_obj(module):
    obj = []

    out = get_config(module, flags='| include ip route-static')

    for line in out.splitlines():
        route = {}
        match = re.search(r'ip route-static\s*(?P<vrf>vpn-instance \S+)?\s*(?P<prefix>\d+.\d+.\d+.\d+)\s+'
                          r'(?P<mask>\d+.\d+.\d+.\d+)\s*(?P<intr>\S+)?\s*(?P<next_hop>\d+.\d+.\d+.\d+)?\s*'
                          r'(?P<adm_dist>preference \d+)?\s*(?P<tag>tag \d+)?\s*(?P<track>track nqa \S+ \S+)?\s*'
                          r'(?P<name>description \S+)?', line)
        if match:
            if match.group('vrf'):
                route.update({'vrf': match.group('vrf').replace('vpn-instance ', '')})
            if match.group('prefix'):
                route.update({'prefix': match.group('prefix')})
            if match.group('mask'):
                route.update({'mask': match.group('mask')})
            if match.group('intr') and not validate_ip_address(match.group('intr')):
                route.update({'interface': match.group('intr')})
                if match.group('next_hop'):
                    route.update({'next_hop': match.group('next_hop')})
            if match.group('intr') and validate_ip_address(match.group('intr')):
                route.update({'next_hop': match.group('intr')})
            if match.group('adm_dist'):
                route.update({'admin_distance': match.group('adm_dist').replace('preference ', '')})
            if match.group('tag'):
                route.update({'tag': match.group('tag').replace('tag ', '')})
            if match.group('track'):
                route.update({'track': match.group('track').replace('track nqa ', '')})
            if match.group('name'):
                route.update({'name': match.group('name').replace('description ', '')})

        obj.append(route)
    return obj


def map_params_to_obj(module, required_together=None):
    keys = ['prefix', 'mask', 'state', 'next_hop', 'vrf', 'interface', 'name', 'admin_distance', 'track', 'tag']
    obj = []

    aggregate = module.params.get('aggregate')
    if aggregate:
        for item in aggregate:
            route = item.copy()
            for key in keys:
                if route.get(key) is None:
                    route[key] = module.params.get(key)

            route = dict((k, v) for k, v in route.items() if v is not None)
            module._check_required_together(required_together, route)
            obj.append(route)
    else:
        module._check_required_together(required_together, module.params)
        route = dict()
        for key in keys:
            if module.params.get(key) is not None:
                route[key] = module.params.get(key)
        obj.append(route)

    return obj


def main():
    """ main entry point for module execution
    """
    element_spec = dict(
        prefix=dict(type='str'),
        mask=dict(type='str'),
        next_hop=dict(type='str'),
        vrf=dict(type='str'),
        interface=dict(type='str'),
        name=dict(type='str', aliases=['description']),
        admin_distance=dict(type='str'),
        track=dict(type='str'),
        tag=dict(tag='str'),
        state=dict(default='present', choices=['present', 'absent'])
    )

    aggregate_spec = deepcopy(element_spec)
    aggregate_spec['prefix'] = dict(required=True)

    # remove default in aggregate spec, to handle common arguments
    remove_default_spec(aggregate_spec)

    argument_spec = dict(
        aggregate=dict(type='list', elements='dict', options=aggregate_spec),
    )

    argument_spec.update(element_spec)
    argument_spec.update(huawei_s_argument_spec)

    required_one_of = [['aggregate', 'prefix']]
    required_together = [['prefix', 'mask']]
    mutually_exclusive = [['aggregate', 'prefix']]

    module = AnsibleModule(argument_spec=argument_spec,
                           required_one_of=required_one_of,
                           mutually_exclusive=mutually_exclusive,
                           supports_check_mode=True)

    warnings = list()
    check_args(module, warnings)

    result = {'changed': False}
    if warnings:
        result['warnings'] = warnings
    want = map_params_to_obj(module, required_together=required_together)
    have = map_config_to_obj(module)

    commands = map_obj_to_commands(want, have)
    result['commands'] = commands

    if commands:
        if not module.check_mode:
            load_config(module, commands)

        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()
