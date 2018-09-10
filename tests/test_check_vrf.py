import json
import pytest
from tasks import check_vrf_status


@pytest.fixture
def set_vendor_specifics(scope="session"):
    with open('vendor_specifics.json', 'r', encoding='utf-8')as jsonf:
        vendor_specs = json.load(jsonf)
    return vendor_specs


def get_file_contents(file_name):
    with open('tests/cmd_outputs/{}'.format(file_name), 'r',
              encoding='utf-8') as in_file:
        contents = in_file.read()
    return contents


def test_find_vrf(set_vendor_specifics):
    vendor_specs = set_vendor_specifics
    cisco_output = get_file_contents('cisco_show_vrf.txt')
    assert "not found" in check_vrf_status.find_vrf(
            'Galaxy', vendor_specs['Cisco Nexus'], None, cisco_output)
    assert "present" in check_vrf_status.find_vrf(
            'Lasers', vendor_specs['Cisco Nexus'], None, cisco_output)
    huawei_output = get_file_contents('huawei_show_vrf.txt')
    assert "not found" in check_vrf_status.find_vrf(
            'Galaxy', vendor_specs['Huawei CE'], None, huawei_output)
    assert "present" in check_vrf_status.find_vrf(
            'Lasers', vendor_specs['Huawei CE'], None, huawei_output)


def test_get_vrf_interfaces(set_vendor_specifics):
    vendor_specs = set_vendor_specifics
    cisco_output_t = get_file_contents('cisco_vrf_interfaces_present.txt')
    cisco_output_f = get_file_contents('cisco_vrf_interfaces_absent.txt')
    huawei_output_t = get_file_contents('huawei_vrf_interfaces_present.txt')
    huawei_output_f = get_file_contents('huawei_vrf_interfaces_absent.txt')
    assert len(check_vrf_status.get_vrf_interfaces(
               'Star', vendor_specs['Cisco Nexus'], 'nxos', None,
               cisco_output_t)) == 3
    assert len(check_vrf_status.get_vrf_interfaces(
               'Star', vendor_specs['Cisco Nexus'], 'nxos', None,
               cisco_output_f)) == 0
    assert len(check_vrf_status.get_vrf_interfaces(
               'Star', vendor_specs['Huawei CE'], 'huawei_vrpv8', None,
               huawei_output_t)) == 2
    assert len(check_vrf_status.get_vrf_interfaces(
               'Star', vendor_specs['Huawei CE'], 'huawei_vrpv8', None,
               huawei_output_f)) == 0
