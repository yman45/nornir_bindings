import re
from nornir.core.task import Result
from app_exception import UnsupportedNOS
from utils.switch_objects import SwitchInterface


def find_vrf(task):
    connection = task.host.get_connection('netmiko')
    output = connection.send_command(task.host['vendor_vars']['show vrf'])
    if not re.search(task.host['vendor_vars']['vrf regexp'].format(
            task.host['vrf_name']), output):
        return Result(host=task.host, failed=True,
                      result='VRF {} is not exist on device'.format(
                          task.host['vrf_name']))
    else:
        return Result(host=task.host,
                      result='VRF {} configured on device'.format(
                        task.host['vrf_name']))


def get_vrf_interfaces(task):
    connection = task.host.get_connection('netmiko')
    output = connection.send_command(
            task.host['vendor_vars']['show vrf interfaces'].format(
                task.host['vrf_name']))
    if task.host['nornir_nos'] == 'nxos':
        if task.host['vrf_name'] not in output:
            interfaces_list = []
        else:
            interfaces_list = [SwitchInterface(
                x.split(' ')[0], mode='routed') for x in output.strip().split(
                    '\n')[1:]]
    elif task.host['nornir_nos'] == 'huawei_vrpv8':
        if 'Interface Number : 0' in output:
            interfaces_list = []
        else:
            start_mark = 'Interface list : '
            start = output.index(start_mark)
            interfaces_list = [SwitchInterface(
                x.strip(' ,'), mode='routed') for x in output[start+len(
                    start_mark):].strip().split('\n')]
    else:
        raise UnsupportedNOS(
                'task received unsupported NOS - {}'.format(
                    task.host['nornir_nos']))
    task.host['interfaces'] = interfaces_list
    return Result(
            host=task.host, result='Interfaces bound to VRF {}:\n\t{}'.format(
                task.host['vrf_name'], '\n\t'.join(
                    [x.name for x in interfaces_list])))
