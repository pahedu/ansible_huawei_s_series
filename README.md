## ABOUT

Huawei S Series Switch support for using Ansible to deploy devices. The Huawei S Series Ansible library, enables you to use Ansible to perform specific operational and configuration tasks on S Series devices.

## OVERVIEW OF MODULES

- huawei_s_banner - Manages shell and login banner.
- huawei_s_command - Run arbitrary command on Huawei S series devices.
- huawei_s_config - Manage Huawei S series configuration sections.
- huawei_s_facts - Gets facts about Huawei S series switches.
- huawei_s_interface - Manages physical attributes of interfaces.
- huawei_s_l2_interfaces - Manage L2 attributes for physical interfaces.
- huawei_s_l3_interface - Manages L3 attributes for IPv4 and IPv6 interfaces.
- huawei_s_lacp - Manages global LACP settings.
- huawei_s_lacp_interfaces - Manages interface LACP settings.
- huawei_s_lag_interface - Configure LAG interface and members.
- huawei_s_lldp_global - Manages global parameters of LLDP.
- huawei_s_lldp_interfaces - Manages interface parameters of LLDP.
- huawei_s_ntp - Manages core NTP configuration.
- huawei_s_ping - Execute ping commands on device.
- huawei_s_static_route - Manages static route configuration.
- huawei_s_vlan - Manages VLAN resources and attributes.



## INSTALLATION

Circumstance instruction:
Ansible network module is suitable for Ansible version 2.9.

Main steps:

- Install suitable Ansible
- Install Huawei S Series switch Ansible library

## EXAMPLE USAGE
An example of static manifest for S Series switch is followed. The network functions is satisfied based on the assumed that Ansible module is available.
```
root@localhost:~# ansible -m huawei_s_command -a "commands='display vlan summary' transport='cli' host=192.168.1.1 port=22 username=huawei password=huawei123" localhost --connection local
localhost | SUCCESS => {
    "changed": false, 
    "stdout": [
        "Number of static VLAN: 3\nVLAN ID: 1 4001 to 4002 \n\nNumber of dynamic VLAN: 0\nVLAN ID: \n\nNumber of service VLAN: 62\nVLAN ID: 4030 to 4060 4064 to 4094 "
    ], 
    "stdout_lines": [
        [
            "Number of static VLAN: 3", 
            "VLAN ID: 1 4001 to 4002 ", 
            "", 
            "Number of dynamic VLAN: 0", 
            "VLAN ID: ", 
            "", 
            "Number of service VLAN: 62", 
            "VLAN ID: 4030 to 4060 4064 to 4094 "
        ]
    ], 
    "warnings": []
}
```

## DEPENDENCIES

These modules require the following to be installed on the Ansible server:

* Python 2.6 or later
* [Ansible](https://github.com/ansible/ansible) 2.9 or later

## REFERENCES
* [Ansible](http://www.ansible.com)
* [Huawei support](http://e.huawei.com/en/marketing-material/onLineView?MaterialID=%7bE9BED27C-914F-456A-9FB5-ACB1ED201190%7d)
