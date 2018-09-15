import json
from nornir.core import InitNornir
from nornir.plugins.functions.text import print_result
from utils.nornir_utils import nornir_set_credentials
from tasks import check_vrf_status
from app_exception import AppException


class UnsupportedNOS(AppException):
    pass


def check_vrf(task, vrf_name):
    with open('tasks/vendor_vars.json', 'r', encoding='utf-8') as jsonf:
        vendor_vars = json.load(jsonf)
    if task.host['nornir_nos'] == 'nxos':
        task.host['vendor_vars'] = vendor_vars['Cisco Nexus']
    elif task.host['nornir_nos'] == 'huawei_vrpv8':
        task.host['vendor_vars'] = vendor_vars['Huawei CE']
    else:
        raise UnsupportedNOS('{} is unsupported or bogus'.format(
            task.host['nornir_nos']))
    task.host['vrf_name'] = vrf_name
    task.run(task=check_vrf_status.find_vrf,
             name='Check if VRF exists on node')
    task.run(task=check_vrf_status.get_vrf_interfaces,
             name='Get VRF interfaces list')


nrnr = InitNornir(config_file='config.yml')
nornir_set_credentials(nrnr)
vrf_name = input('Enter VRF name > ')
result = nrnr.run(task=check_vrf, vrf_name=vrf_name)
print_result(result)
