from unittest.mock import Mock
from nornir.core.inventory import Host
from nornir.core.task import Task


class OvercomeHostSlots(Host):
    '''Class to overcome Nornir 2.0 inventory classes attributes storing with
    slots, which makes them read-only. This child class adds get_connection
    method to slots, which makes possible to mock it later.
    This is probably not a good idea. Maybe all connection handling in this
    repository is done wrong. But it is working like this now.'''
    __slots__ = ("get_connection")


def get_file_contents(file_name):
    '''Open file with CLI outputs and return its contents.
    Arguments:
        * file_name - file name that resides in cmd_outputs directory
    Returns:
        * string with file contents
    '''
    with open('tests/cmd_outputs/{}'.format(file_name), 'r',
              encoding='utf-8') as in_file:
        contents = in_file.read()
    return contents


def create_fake_task(output, vendor_vars, vrf_name, nos, test_obj,
                     effect=None):
    '''Create instance of nornir.core.task.Task and nornir.core.task.Host,
    assign latter to former, but mocking Host get_connection method to not
    really connect to hosts and return files outputs. Can use single return
    value or side effect with list of files.
    Arguments:
        * output - string with CLI output of some command, if we need single
            output
        * vendor_vars - dict with NOS CLI commands
        * vrf_name - name of VRF to test upon
        * nos - NOS name
        * test_obj - instance of nornir.core.task.Task which we will test
        * effect (defaults to None) - Mock.side_effect to provide different
            outputs
    Returns:
        * instance of nornir.core.task.Task with mocked internals
    '''
    connection = Mock()
    if effect is None:
        connection.send_command = Mock(return_value=output)
    else:
        connection.send_command = Mock(side_effect=effect)
    host = OvercomeHostSlots('test-host')
    host['vendor_vars'] = vendor_vars
    host['vrf_name'] = vrf_name
    host.platform = nos
    host.get_connection = Mock(return_value=connection)
    fake_task = Task(test_obj)
    fake_task.host = host
    return fake_task
