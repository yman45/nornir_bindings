from unittest.mock import Mock
from nornir.core.inventory import Host
from nornir.core.task import Task


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
