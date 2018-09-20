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


def check_interfaces_status(task, interface_list=None):
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    connection = task.host.get_connection('netmiko')
    result = 'Interfaces status:\n'
    interfaces_brief_output = connection.send_command(task.host['vendor_vars'][
        'show interfaces brief'])
    for interface in task.host['interfaces']:
        if task.host['nornir_nos'] == 'nxos':
            interface_name = cisco_compact_name(interface.name)
        else:
            interface_name = interface.name
        brief_line_start = interfaces_brief_output.index(interface_name)
        # 'find' in a next line will cover end of output (last line) situations
        brief_line_end = interfaces_brief_output.find('\n', brief_line_start)
        brief_line = interfaces_brief_output[brief_line_start:brief_line_end]
        if task.host['nornir_nos'] == 'nxos':
            if ' up ' in brief_line:
                interface.admin_status = 'up'
                interface.oper_status = 'up'
            elif 'Administratively down' in brief_line:
                interface.admin_status = 'down'
                interface.oper_status = 'down'
            else:
                interface.admin_status = 'up'
                interface.oper_status = 'down'
        elif task.host['nornir_nos'] == 'huawei_vrpv8':
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
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                task.host['nornir_nos']))
        result += 'Interface {} is in {}/{} state\n'.format(
                interface.name, interface.admin_status, interface.oper_status)
    return Result(host=task.host, result=result)


def get_interfaces_ip_addresses(task, interface_list=None):
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    result = 'IP addresses on interfaces:\n'
    connection = task.host.get_connection('netmiko')
    for interface in task.host['interfaces']:
        ipv4_status = connection.send_command(
            task.host['vendor_vars']['show ipv4 interface'].format(
                interface.name))
        ipv6_status = connection.send_command(
            task.host['vendor_vars']['show ipv6 interface'].format(
                interface.name))
        if task.host['nornir_nos'] == 'nxos':
            if 'IP is disabled' not in ipv4_status:
                pattern = re.compile(
                        r'IP address: '
                        r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                        r', '
                        r'IP subnet: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
                        r'/(\d{1,2})( secondary)?')
                match = pattern.findall(ipv4_status)
                for address in match:
                    interface.ipv4_addresses.append(IPAddress(
                            address[0], address[1], address[2]))
            if 'IPv6 is disabled' not in ipv6_status:
                primary_address = re.search(r'IPv6 address: (\S+)',
                                            ipv6_status).group(1)
                primary_prefix_length = re.search(
                        r'IPv6 subnet:  \S+/(\d{1,3})', ipv6_status).group(1)
                link_local = re.search(r'IPv6 link-local address: (\S+)',
                                       ipv6_status).group(1)
                interface.ipv6_addresses.append(IPAddress(
                    primary_address, primary_prefix_length))
                interface.ipv6_addresses.append(IPAddress(
                    link_local, '64', True))
                sec_start = ipv6_status.find('Secondary configured addresses')
                if sec_start != -1:
                    sec_end = ipv6_status.index('IPv6 link-local address')
                    match = re.findall(r'([0-9A-Fa-f:]+)/(\d{1,3})',
                                       ipv6_status[sec_start:sec_end])
                    for address in match:
                        interface.ipv6_addresses.append(IPAddress(
                            address[0], address[1], True))
        elif task.host['nornir_nos'] == 'huawei_vrpv8':
            if 'Internet Address is' in ipv4_status:
                pattern = re.compile(r'Internet Address is '
                                     r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                                     r'/(\d{1,2})( Sub)?')
                match = pattern.findall(ipv4_status)
                for address in match:
                    interface.ipv4_addresses.append(IPAddress(
                        address[0], address[1], address[2]))
            if 'The IPv6 address does not exist' not in ipv6_status:
                interface.ipv6_addresses.append(IPAddress(re.search(
                    r'link-local address is ([0-9A-Fa-f:]+)',
                    ipv6_status).group(1), '64', True))
                match = re.findall(
                        r'([0-9A-Fa-f:]+), subnet is [0-9A-Fa-f:]+/(\d{1,3})',
                        ipv6_status)
                for address in match:
                    interface.ipv6_addresses.append(IPAddress(
                        address[0], address[1], True))
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                task.host['nornir_nos']))
        result += 'Interface {} IP addresses:\n'
        if len(interface.ipv4_addresses) == 0:
            result += '\tNo IPv4 addresses\n'
        else:
            result += '\tIPv4: {}\n'.format(', '.join(
                str(interface.ipv4_addresses)))
        if len(interface.ipv6_addresses) == 0:
            result += '\tNo IPv6 addresses\n'
        else:
            result += '\tIPv6: {}\n'.format(', '.join(
                str(interface.ipv6_addresses)))
    return Result(host=task.host, result=result)
