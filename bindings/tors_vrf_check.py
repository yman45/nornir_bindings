import json
from nornir.core import InitNornir
from nornir.plugins.functions.text import print_result
from nornir.core.task import Result
from utils.nornir_utils import nornir_set_credentials
from tasks import check_vrf_status
from app_exception import AppException


class UnsupportedNOS(AppException):
    pass


def check_vrf(task, vrf_name):
    with open('vendor_specifics.json', 'r', encoding='utf-8') as jsonf:
        vendor_specs = json.load(jsonf)
    if task.host["nornir_nos"] == "nxos":
        vendor_dict = vendor_specs['Cisco Nexus']
    elif task.host["nornir_nos"] == 'huawei_vrpv8':
        vendor_dict = vendor_specs['Huawei CE']
    else:
        raise UnsupportedNOS("{} is unsupported or bogus".format(
            task.host["nornir_nos"]))
    connection = task.host.get_connection("netmiko")
    vrf_present = check_vrf_status.find_vrf(vrf_name, vendor_dict, connection)
    if 'not found' in vrf_present:
        return Result(host=task.host, result=vrf_present)
    vrf_interfaces = check_vrf_status.get_vrf_interfaces(
            vrf_name, vendor_dict, task.host["nornir_nos"], connection)
    result = "Interfaces in VRF {}:\n\t{}".format(vrf_name, '\n\t'.join(
        [x.name for x in vrf_interfaces]))
    return Result(host=task.host, result=result)


nrnr = InitNornir(config_file="config.yml")
nornir_set_credentials(nrnr)
vrf_name = input('Enter VRF name > ')
result = nrnr.run(task=check_vrf, vrf_name=vrf_name)
print_result(result)
