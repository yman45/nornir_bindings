import re
from nornir.core.task import Result
from app_exception import UnsupportedNOS
from utils.switch_objects import SwitchInterface, IPAddress


def cisco_compact_name(int_name):
    if 'Ethernet' in int_name:
        return 'Eth'+int_name[8:]
    elif 'port-channel' in int_name:
        return 'Po'+int_name[12:]
    else:
        return int_name


def parse_cisco_int_status(interface, brief_out, v4_out, v6_out):
    ccn = cisco_compact_name(interface.name)
    brief_line_start = brief_out.index(ccn)
    brief_line_end = brief_out.find('\n', brief_line_start)
    brief_line = brief_out[brief_line_start:brief_line_end]
    if ' up ' in brief_line:
        interface.admin_status = 'up'
        interface.oper_status = 'up'
    elif 'Administratively down' in brief_line:
        interface.admin_status = 'down'
        interface.oper_status = 'down'
    else:
        interface.admin_status = 'up'
        interface.oper_status = 'down'
    if 'IP is disabled' not in v4_out:
        pattern = re.compile(r'IP address: '
                             r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                             r', '
                             r'IP subnet: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
                             r'/(\d{1,2})( secondary)?')
        match = pattern.findall(v4_out)
        for address in match:
            interface.ipv4_addresses.append(IPAddress(
                    address[0], address[1], address[2]))
    if 'IPv6 is disabled' not in v6_out:
        primary_address = re.search(r'IPv6 address: (\S+)',
                                    v6_out).group(1)
        primary_prefix_length = re.search(r'IPv6 subnet:  \S+/(\d{1,3})',
                                          v6_out).group(1)
        link_local = re.search(r'IPv6 link-local address: (\S+)',
                               v6_out).group(1)
        interface.ipv6_addresses.append(IPAddress(
            primary_address, primary_prefix_length))
        interface.ipv6_addresses.append(IPAddress(
            link_local, '64', True))
        sec_start = v6_out.find('Secondary configured addresses')
        if sec_start != -1:
            sec_end = v6_out.index('IPv6 link-local address')
            match = re.findall(r'([0-9A-Fa-f:]+)/(\d{1,3})',
                               v6_out[sec_start:sec_end])
            for address in match:
                interface.ipv6_addresses.append(IPAddress(
                    address[0], address[1], True))


def parse_huawei_int_status(interface, brief_out, v4_out, v6_out):
    brief_line_start = brief_out.index(interface.name)
    brief_line_end = brief_out.find('\n', brief_line_start)
    brief_line = brief_out[brief_line_start:brief_line_end]
    phy_status = re.search(r'{}(\(.+\))?\s+(\*?(down|up))'.format(
        interface.name), brief_line).group(2)
    if phy_status == '*down':
        interface.admin_status = 'down'
        interface.oper_status = 'down'
    elif phy_status == 'down':
        interface.admin_status = 'up'
        interface.oper_status = 'down'
    else:
        interface.admin_status = 'up'
        interface.oper_status = 'up'
    if 'Internet Address is' in v4_out:
        pattern = re.compile(r'Internet Address is '
                             r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                             r'/(\d{1,2})( Sub)?')
        match = pattern.findall(v4_out)
        for address in match:
            interface.ipv4_addresses.append(IPAddress(
                address[0], address[1], address[2]))
    if 'The IPv6 address does not exist' not in v6_out:
        interface.ipv6_addresses.append(IPAddress(re.search(
            r'link-local address is ([0-9A-Fa-f:]+)',
            v6_out).group(1), '64', True))
        match = re.findall(
                r'([0-9A-Fa-f:]+), subnet is [0-9A-Fa-f:]+/(\d{1,3})',
                v6_out)
        for address in match:
            interface.ipv6_addresses.append(IPAddress(
                address[0], address[1], True))


def check_interfaces_state(task, interface_list=None):
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    connection = task.host.get_connection('netmiko')
    brief_ints_output = connection.send_command(task.host['vendor_vars'][
        'show interfaces brief'])
    ipv4_statuses = [connection.send_command(
        task.host['vendor_vars']['show ipv4 interface'].format(
            x)) for x in task.host['interfaces']]
    ipv6_statuses = [connection.send_command(
        task.host['vendor_vars']['show ipv6 interface'].format(
            x)) for x in task.host['interfaces']]
    if task.host['nornir_nos'] == 'nxos':
        for num, interface in enumerate(task.host['interfaces']):
            parse_cisco_int_status(interface, brief_ints_output,
                                   ipv4_statuses[num], ipv6_statuses[num])
    elif task.host['nornir_nos'] == 'huawei_vrpv8':
        for num, interface in enumerate(task.host['interfaces']):
            parse_huawei_int_status(interface, brief_ints_output,
                                    ipv4_statuses[num], ipv6_statuses[num])
    else:
        raise UnsupportedNOS(
                'task received unsupported NOS - {}'.format(
                    task.host['nornir_nos']))
    result = 'Interfaces states:\n'
    for i in task.host['interfaces']:
        result += '\t{}: Admin - {}, Oper - {}\n'.format(
                i.name, i.admin_status, i.oper_status)
        if len(i.ipv4_addresses) == 0:
            result += '\t\tNo IPv4 addresses\n'
        else:
            result += '\t\tIPv4 addresses:\n'
            for address in i.ipv4_addresses:
                result += '\t\t\t{}/{}\n'.format(address.address,
                                                 address.prefix_length)
        if len(i.ipv6_addresses) == 0:
            result += '\t\tNo IPv6 addresses\n'
        else:
            result += '\t\tIPv6 addresses:\n'
            for address in i.ipv6_addresses:
                result += '\t\t\t{}/{}\n'.format(address.address,
                                                 address.prefix_length)
    return Result(host=task.host, result=result)
