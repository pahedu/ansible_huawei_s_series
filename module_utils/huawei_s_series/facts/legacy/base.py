# -*- coding: utf-8 -*-
# Copyright 2019 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
The huaiwe_s legacy fact class
It is in this file the configuration is collected from the device
for a given resource, parsed, and the facts tree is populated
based on the configuration.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type


import platform
import re

from ansible.module_utils.network.huawei_s_series.huawei_s import run_commands, get_capabilities
from ansible.module_utils.network.huawei_s_series.huawei_s import normalize_interface
from ansible.module_utils.six import iteritems
from ansible.module_utils.six.moves import zip


class FactsBase(object):

    COMMANDS = list()

    def __init__(self, module):
        self.module = module
        self.facts = dict()
        self.warnings = list()
        self.responses = None

    def populate(self):
        self.responses = run_commands(self.module, commands=self.COMMANDS, check_rc=False)

    def run(self, cmd):
        return run_commands(self.module, commands=cmd, check_rc=False)


class Default(FactsBase):

    COMMANDS = ['display version', 'display device manufacture-info', 'display stack']

    def populate(self):
        super(Default, self).populate()
        self.facts.update(self.platform_facts())
        data = self.responses[0]
        if data:
            self.facts['serialnum'] = self.parse_serialnum(data)
            self.parse_stacks(data)

    def parse_serialnum(self, data):
        data = self.responses[1]
        match = re.search(r'\d+\s*\S+\s*(\S+)\s*\d+-\d+-\d+', data)
        if match:
            return match.group(1)

    def parse_stacks(self, data):
        data = self.responses[2]
        match = re.findall(r'^\d+\s*\S+\s*\S+\s+\d+\s+(\S+)', data, re.M)
        if match:
            self.facts['stacked_models'] = match

        data = self.responses[1]
        match = re.findall(r'^\d+\s*\S+\s*(\S+)\s*\d+-\d+-\d+', data, re.M)
        if match:
            self.facts['stacked_serialnums'] = match

    def platform_facts(self):
        platform_facts = {}

        resp = get_capabilities(self.module)
        device_info = resp['device_info']

        platform_facts['system'] = device_info['network_os']

        for item in ('model', 'image', 'version', 'platform', 'hostname'):
            val = device_info.get('network_os_%s' % item)
            if val:
                platform_facts[item] = val

        platform_facts['api'] = resp['network_api']
        platform_facts['python_version'] = platform.python_version()

        return platform_facts


class Hardware(FactsBase):

    COMMANDS = [
        'dir',
        'display memory-usage'
    ]

    def populate(self):
        warnings = list()
        super(Hardware, self).populate()
        data = self.responses[0]
        if data:
            self.facts['filesystems'] = self.parse_filesystems(data)
            self.facts['filesystems_info'] = self.parse_filesystems_info(data)

        data = self.responses[1]
        if data:
            if 'Invalid input detected' in data:
                warnings.append('Unable to gather memory statistics')
            else:
                match_total = re.search(r'^\s*[Ss]ystem\s+[Tt]otal\s+[Mm]emory\s+[Ii]s\s*:\s*(\d*)', data, re.M)
                match_used = re.search(r'^\s*[Tt]otal\s+[Mm]emory\s+[Uu]sed\s+[Ii]s\s*:\s*(\d+)', data, re.M)
                match_free = int(match_total.group(1)) - int(match_used.group(1))
                if match_total and match_free:
                    self.facts['memtotal_mb'] = int(match_total.group(1)) / 1048576
                    self.facts['memfree_mb'] = int(match_free) / 1048576

    def parse_filesystems(self, data):
        return re.findall(r'^Directory of (\S+)/', data, re.M)

    def parse_filesystems_info(self, data):
        facts = dict()
        fs = ''
        for line in data.split('\n'):
            match = re.match(r'^Directory of (\S+)/', line)
            if match:
                fs = match.group(1)
                facts[fs] = dict()
                continue
            match = re.match(r'^(\S+) KB total \((\S+) KB free\)', line)
            if match:
                match_total = ''.join(match.group(1).split(','))
                match_free = ''.join(match.group(2).split(','))
                facts[fs]['spacetotal_kb'] = int(match_total)
                facts[fs]['spacefree_kb'] = int(match_free)
        return facts


class Config(FactsBase):

    COMMANDS = ['display current-configuration']

    def populate(self):
        super(Config, self).populate()
        data = self.responses[0]
        if data:
            data = re.sub(
                r'^Software Version \S+\n',
                '', data, flags=re.MULTILINE)
            self.facts['config'] = data


class Interfaces(FactsBase):

    COMMANDS = [
        'display interface',
        'display ip interface',
        'display ipv6 interface',
        'display lldp local',
        'display cdp local'
    ]

    def populate(self):
        super(Interfaces, self).populate()

        self.facts['all_ipv4_addresses'] = list()
        self.facts['all_ipv6_addresses'] = list()
        self.facts['neighbors'] = {}

        data = self.responses[0]
        if data:
            interfaces = self.parse_interfaces(data)
            self.facts['interfaces'] = self.populate_interfaces(interfaces)

        data = self.responses[1]
        if data:
            data = self.parse_interfaces(data)
            self.populate_ipv4_interfaces(data)

        data = self.responses[2]
        if data:
            data = self.parse_interfaces(data)
            self.populate_ipv6_interfaces(data)

        data = self.responses[3]
        lldp_errs = ['Invalid input', 'Info: Global LLDP is not enabled.']

        if data and not any(err in data for err in lldp_errs):
            neighbors = self.run(['display lldp neighbor'])
            if neighbors:
                self.facts['neighbors'].update(self.parse_neighbors(neighbors[0]))

        data = self.responses[4]
        cdp_errs = ['Info: Global LLDP is not enabled.']

        if data and not any(err in data for err in cdp_errs):
            cdp_neighbors = self.run(['display cdp neighbor'])
            if cdp_neighbors:
                self.facts['neighbors'].update(self.parse_cdp_neighbors(cdp_neighbors[0]))

    def populate_interfaces(self, interfaces):
        facts = dict()
        for key, value in iteritems(interfaces):
            intf = dict()
            intf['description'] = self.parse_description(value)
            intf['macaddress'] = self.parse_macaddress(value)

            intf['mtu'] = self.parse_mtu(value)
            intf['bandwidth'] = self.parse_bandwidth(value)
            intf['mediatype'] = self.parse_mediatype(value)
            intf['duplex'] = self.parse_duplex(value)
            intf['lineprotocol'] = self.parse_lineprotocol(value)
            intf['operstatus'] = self.parse_operstatus(value)
            intf['type'] = self.parse_type(value)

            facts[key] = intf
        return facts

    def populate_ipv4_interfaces(self, data):
        for key, value in data.items():
            self.facts['interfaces'][key]['ipv4'] = list()
            primary_address = addresses = []
            primary_address = re.findall(r'[Ii]nternet [Aa]ddress is (\S+)', value, re.M)
            addresses = re.findall(r'[Ii]nternet [Aa]ddress is (\S+)\s+Sub', value, re.M)
            if len(primary_address) == 0:
                continue
            addresses.append(primary_address[0])
            for address in addresses:
                addr, subnet = address.split("/")
                ipv4 = dict(address=addr.strip(), subnet=subnet.strip())
                self.add_ip_address(addr.strip(), 'ipv4')
                self.facts['interfaces'][key]['ipv4'].append(ipv4)

    def populate_ipv6_interfaces(self, data):
        for key, value in iteritems(data):
            try:
                self.facts['interfaces'][key]['ipv6'] = list()
            except KeyError:
                self.facts['interfaces'][key] = dict()
                self.facts['interfaces'][key]['ipv6'] = list()
            addresses = re.findall(r'\s+(.+), subnet', value, re.M)
            subnets = re.findall(r', subnet is (.+)$', value, re.M)
            for addr, subnet in zip(addresses, subnets):
                ipv6 = dict(address=addr.strip(), subnet=subnet.strip())
                self.add_ip_address(addr.strip(), 'ipv6')
                self.facts['interfaces'][key]['ipv6'].append(ipv6)

    def add_ip_address(self, address, family):
        if family == 'ipv4':
            self.facts['all_ipv4_addresses'].append(address)
        else:
            self.facts['all_ipv6_addresses'].append(address)

    def parse_neighbors(self, neighbors):
        facts = dict()
        for entry in neighbors.split('Maximum frame Size       :'):
            if entry == '':
                continue
            intf = self.parse_lldp_intf(entry)
            if intf is None:
                return facts
            intf = normalize_interface(intf)
            if intf not in facts:
                facts[intf] = list()
            fact = dict()
            fact['host'] = self.parse_lldp_host(entry)
            fact['port'] = self.parse_lldp_port(entry)
            facts[intf].append(fact)
        return facts

    def parse_cdp_neighbors(self, neighbors):
        facts = dict()
        for entry in neighbors.split('-------------------------'):
            if entry == '':
                continue
            intf_port = self.parse_cdp_intf_port(entry)
            if intf_port is None:
                return facts
            intf, port = intf_port
            if intf not in facts:
                facts[intf] = list()
            fact = dict()
            fact['host'] = self.parse_cdp_host(entry)
            fact['port'] = port
            facts[intf].append(fact)
        return facts

    def parse_interfaces(self, data):
        parsed = dict()
        key = ''
        for line in data.split('\n'):
            match = re.match(
                r'^(Vlanif\d+|GigabitEthernet\d+/\d+/\d+|XGigabitEthernet\d+/\d+/\d+|25GE\d+/\d+/\d+|40GE\d+/\d+/\d+|100GE\d+/\d+/\d+)',
                line)
            if match:
                key = match.group(1)
                parsed[key] = line
            elif len(line) == 0:
                continue
            elif key:
                parsed[key] += '\n%s' % line
        return parsed

    def parse_description(self, data):
        match = re.search(r'Description:(.+)$', data, re.M)
        if match:
            return match.group(1)

    def parse_macaddress(self, data):
        match = re.search(r'Hardware address is (\S+)', data)
        if match:
            return match.group(1)

    def parse_ipv4(self, data):
        match = re.search(r'Internet Address is (\S+)', data)
        if match:
            addr, masklen = match.group(1).split('/')
            return dict(address=addr, masklen=int(masklen))

    def parse_mtu(self, data):
        match = re.search(r'The Maximum Transmit Unit is (\d+)', data)
        if match:
            return int(match.group(1))

    def parse_bandwidth(self, data):
        match = re.search(r'Speed : (\d+)', data)
        if match:
            return int(match.group(1))

    def parse_duplex(self, data):
        match = re.search(r'^Duplex\s*:\s*(\w+),', data, re.M)
        if match:
            return match.group(1)

    def parse_mediatype(self, data):
        match = re.search(r'^Port Mode:\s+(\w+\s+\w+)', data, re.M)
        if match:
            return match.group(1)

    def parse_type(self, data):
        match = re.search(r'^(\S+)\d+/\d+/\d+\s+current state', data, re.M)
        if match:
            return match.group(1)

    def parse_lineprotocol(self, data):
        match = re.search(r'Line protocol current state : (\S+)', data, re.M)
        if match:
            return match.group(1)

    def parse_operstatus(self, data):
        match = re.search(r'^(?:.+) current state\s*:\s*(.+)', data, re.M)
        if match:
            return match.group(1)

    def parse_lldp_intf(self, data):
        match = re.search(r'^(\S+)\s+has\s+\d+\s+neighbor', data, re.M)
        if match:
            return match.group(1)

    def parse_lldp_host(self, data):
        match = re.search(r'^[Ss]ystem [Nn]ame\s*:\s*(.+)$', data, re.M)
        if match:
            return match.group(1)

    def parse_lldp_port(self, data):
        match = re.search(r'^[Pp]ort [Ii][Dd]\s*:\s*(\S+)$', data, re.M)
        if match:
            return match.group(1)

    def parse_cdp_intf_port(self, data):
        match = re.search(r'^Interface: (.+),  Port ID \(outgoing port\): (.+)$', data, re.M)
        if match:
            return match.group(1), match.group(2)

    def parse_cdp_host(self, data):
        match = re.search(r'^Device ID: (.+)$', data, re.M)
        if match:
            return match.group(1)