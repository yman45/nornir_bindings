from unittest.mock import Mock
from nornir.core.inventory import Host
from nornir.core.task import Task
from tasks.check_vrf_status import SwitchInterface


def get_file_contents(file_name):
    with open('tests/cmd_outputs/{}'.format(file_name), 'r',
              encoding='utf-8') as in_file:
        contents = in_file.read()
    return contents


def create_fake_task(output, vendor_vars, vrf_name, nos, test_obj,
                     effect=None):
    connection = Mock()
    if effect is None:
        connection.send_command = Mock(return_value=output)
    else:
        connection.send_command = Mock(side_effect=effect)
    host = Host('test-host')
    host['vendor_vars'] = vendor_vars
    host['vrf_name'] = vrf_name
    host['nornir_nos'] = nos
    host.get_connection = Mock(return_value=connection)
    fake_task = Task(test_obj)
    fake_task.host = host
    return fake_task


def interface_name_to_file_name(name):
    trans_dict = {ord(':'): '_',
                  ord('/'): '_',
                  ord('.'): '_',
                  ord('-'): '_'}
    return name.lower().translate(trans_dict)


def create_fake_task_with_host(interface_list, nos, vendor_vars, task_func):
    if nos == 'nxos':
        vendor = 'cisco'
    elif nos == 'huawei_vrpv8':
        vendor = 'huawei'
    file_names = [vendor+'_show_int_brief.txt']
    for interface in interface_list:
        name = interface_name_to_file_name(interface)
        file_names.append(vendor+'_show_ipv4_int_'+name+'.txt')
    for interface in interface_list:
        name = interface_name_to_file_name(interface)
        file_names.append(vendor+'_show_ipv6_int_'+name+'.txt')
    outputs = [get_file_contents(x) for x in file_names]
    task = create_fake_task(None, vendor_vars, None, task_func, effect=outputs)
    task.host['interfaces'] = [SwitchInterface(x) for x in interface_list]
    task.host['nornir_nos'] = nos
    return task
