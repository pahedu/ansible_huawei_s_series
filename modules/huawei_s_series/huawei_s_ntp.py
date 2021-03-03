#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: huawei_s_ntp
extends_documentation_fragment: huawei_s
version_added: "2.9"
short_description: Manages core NTP configuration.
description:
    - Manages core NTP configuration.
author:
    - Aleksandr Natov (@pahedu)
options:
    server:
        description:
            - Network address of NTP server.
    source_int:
        description:
            - Source interface for NTP packets.
    acl:
        description:
            - ACL for peer/server access restricition.
    auth:
        description:
            - Enable NTP authentication. Data type boolean.
        type: bool
        default: False
    auth_key:
        description:
            - hmac-sha256 NTP authentication key. Used with ciper argument, respectively
              use with huawei encoded string with special character escaping
    key_id:
        description:
            - auth_key id. Data type string
    state:
        description:
            - Manage the state of the resource.
        default: present
        choices: ['present', 'absent']
'''

EXAMPLES = '''
# Set new NTP server and source interface
- huawei_s_ntp:
    server: 10.0.255.10
    source_int: Vlanif1
    state: present

# Remove NTP ACL
- huawei_s_ntp:
    acl: 2000
    state: absent

# Set NTP authentication
- huawei_s_ntp:
    key_id: 10
    auth_key: "%^%#LbK;Ln=*S>Na,B3Rr{FFn>:dBzjjGM&QH'V&@|;~09<{G`&4m(Ce=TTM\\Gn*%^%#" #Use escape character
    auth: true
    state: present

# Set new NTP configuration
- huawei_s_ntp:
    server: 10.0.255.10
    source_int: Vlanif1
    acl: 2000
    key_id: 10
    auth_key: "%^%#LbK;Ln=*S>Na,B3Rr{FFn>:dBzjjGM&QH'V&@|;~09<{G`&4m(Ce=TTM\\Gn*%^%#" #Use escape character
    auth: true
    state: present
'''

RETURN = '''
commands:
    description: command sent to the device
    returned: always
    type: list
    sample: ["undo ntp-service unicast-server 10.0.255.10", "undo ntp-service source-interface Loopback0"]
'''
import re

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.huawei_s_series.huawei_s import get_config, load_config
from ansible.module_utils.network.huawei_s_series.huawei_s import huawei_s_argument_spec, check_args


def parse_server(line, dest):
    if dest == 'unicast-server':
        match = re.search(r'(ntp-service unicast-server )(\d+\.\d+\.\d+\.\d+)', line, re.M)
        if match:
            server = match.group(2)
            return server


def parse_source_int(line, dest):
    if dest == 'source-interface':
        match = re.search(r'(ntp-service source-interface )(\S+)', line, re.M)
        if match:
            source = match.group(2)
            return source


def parse_acl(line, dest):
    if dest == 'access':
        match = re.search(r'ntp-service access (?:peer|serve)(?:\s+)(\S+)', line, re.M)
        if match:
            acl = match.group(1)
            return acl


def parse_auth_key(line, dest):
    if dest == 'authentication-keyid':
        match = re.search(r'ntp-service authentication-keyid \d+ authentication-mode (?:hmac-sha256|md5) cipher (\S+)', line, re.M)
        if match:
            auth_key = match.group(1)
            return auth_key


def parse_key_id(line, dest):
    if dest == 'reliable':
        match = re.search(r'(ntp-service reliable authentication-keyid )(\d+)', line, re.M)
        if match:
            auth_key = match.group(2)
            return auth_key


def parse_auth(dest):
    if dest == 'authentication':
        return dest


def map_config_to_obj(module):

    obj_dict = {}
    obj = []
    server_list = []

    config = get_config(module, flags=['| include ntp-service'])

    for line in config.splitlines():
        match = re.search(r'ntp-service (\S+)', line, re.M)
        if match:
            dest = match.group(1)

            server = parse_server(line, dest)
            source_int = parse_source_int(line, dest)
            acl = parse_acl(line, dest)
            auth = parse_auth(dest)
            auth_key = parse_auth_key(line, dest)
            key_id = parse_key_id(line, dest)

            if server:
                server_list.append(server)
            if source_int:
                obj_dict['source_int'] = source_int
            if acl:
                obj_dict['acl'] = acl
            if auth:
                obj_dict['auth'] = True
            if auth_key:
                obj_dict['auth_key'] = auth_key
            if key_id:
                obj_dict['key_id'] = key_id

    obj_dict['server'] = server_list
    obj.append(obj_dict)

    return obj


def map_params_to_obj(module):
    obj = []
    obj.append({
        'state': module.params['state'],
        'server': module.params['server'],
        'source_int': module.params['source_int'],
        'acl': module.params['acl'],
        'auth': module.params['auth'],
        'auth_key': module.params['auth_key'],
        'key_id': module.params['key_id']
    })

    return obj


def map_obj_to_commands(want, have, module):

    commands = list()

    server_have = have[0].get('server', None)
    source_int_have = have[0].get('source_int', None)
    acl_have = have[0].get('acl', None)
    auth_have = have[0].get('auth', None)
    auth_key_have = have[0].get('auth_key', None)
    key_id_have = have[0].get('key_id', None)

    for w in want:
        server = w['server']
        source_int = w['source_int']
        acl = w['acl']
        state = w['state']
        auth = w['auth']
        auth_key = w['auth_key']
        key_id = w['key_id']

        if state == 'absent':
            if server_have and server in server_have:
                commands.append('undo ntp-service unicast-server {0}'.format(server))
            if source_int and source_int_have:
                commands.append('undo ntp-service source-interface {0}'.format(source_int))
            if acl and acl_have:
                commands.append('undo ntp-service access peer {0}'.format(acl))
            if auth is True and auth_have:
                commands.append('undo ntp-service authentication enable')
            if key_id and key_id_have:
                commands.append('undo ntp-service reliable authentication-keyid {0}'.format(key_id))
            if auth_key and auth_key_have:
                if key_id and key_id_have:
                    commands.append('undo ntp-service authentication-keyid {0}'.format(key_id))

        elif state == 'present':
            if server is not None and server not in server_have:
                commands.append('ntp-service unicast-server {0}'.format(server))
            if source_int is not None and source_int != source_int_have:
                commands.append('ntp-service source-interface {0}'.format(source_int))
            if acl is not None and acl != acl_have:
                commands.append('ntp-service access peer {0}'.format(acl))
            if auth is not None and auth != auth_have and auth is not False:
                commands.append('ntp-service authentication enable')
            if auth_key is not None and auth_key != auth_key_have:
                if key_id is not None:
                    commands.append('ntp-service authentication-keyid {0} authentication-mode hmac-sha256 cipher {1}'.format(key_id, auth_key))
            if key_id is not None and key_id != key_id_have:
                commands.append('ntp-service reliable authentication-keyid {0}'.format(key_id))


    return commands


def main():

    argument_spec = dict(
        server=dict(),
        source_int=dict(),
        acl=dict(),
        auth=dict(type='bool', default=False),
        auth_key=dict(),
        key_id=dict(),
        state=dict(choices=['absent', 'present'], default='present')
    )

    argument_spec.update(huawei_s_argument_spec)

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    result = {'changed': False}

    warnings = list()
    check_args(module, warnings)
    if warnings:
        result['warnings'] = warnings

    want = map_params_to_obj(module)
    have = map_config_to_obj(module)

    commands = map_obj_to_commands(want, have, module)
    result['commands'] = commands

    if commands:
        if not module.check_mode:
            load_config(module, commands)
        result['changed'] = True

    module.exit_json(**result)


if __name__ == '__main__':
    main()
