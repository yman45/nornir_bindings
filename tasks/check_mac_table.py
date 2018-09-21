import re
from nornir.core.task import Result
from app_exception import UnsupportedNOS
from utils.switch_objects import SwitchInterface


def get_interfaces_macs(task, interface_list=None):
    def count_macs(nos, mac_table):
        if nos == 'nxos':
            delimeter = mac_table.find('---')
            # Cisco returns empty output if no MACs learned
            if delimeter == -1:
                return 0
            else:
                table_start = mac_table.index('\n', delimeter)
                return len(mac_table[table_start:].strip().split('\n'))
        elif nos == 'huawei_vrpv8':
            return int(re.search(r'Total items: (\d+)', mac_table).group(1))
        else:
            raise UnsupportedNOS('task received unsupported NOS - {}'.format(
                nos))
    if interface_list:
        task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    connection = task.host.get_connection('netmiko')
    result = 'MACs learned on interfaces:\n'
    for interface in task.host['interfaces']:
        if interface.svi:
            vlan_id = re.match(r'(?i)^vlan(?:if)?(\d+)$',
                               interface.name).group(1)
            mac_table = connection.send_command(task.host['vendor_vars'][
                'show mac table vlan'].format(vlan_id))
            interface.macs_learned = count_macs(task.host['nornir_nos'],
                                                mac_table)
        elif interface.mode == 'routed':
            interface.macs_learned = 0
            result += '\tInterface {} is routing\n'.format(interface.name)
            continue
        else:
            mac_table = connection.send_command(
                    task.host['vendor_vars'][
                        'show mac table interface'].format(interface.name))
            interface.macs_learned = count_macs(task.host['nornir_nos'],
                                                mac_table)
        result += '\tInterface {} learned {} MACs\n'.format(
                interface.name, interface.macs_learned)
    return Result(host=task.host, result=result)
