import json
from tasks import check_vrf_status


def test_find_vrf():
    with open('vendor_specifics.json', 'r', encoding='utf-8')as jsonf:
        vendor_specs = json.load(jsonf)
    with open('tests/cmd_outputs/cisco_show_vrf.txt',
              'r', encoding='utf-8') as in_file:
        cisco_output = in_file.read()
    assert "not found" in check_vrf_status.find_vrf(
            'Galaxy', vendor_specs['Cisco Nexus'], None, cisco_output)
    assert "present" in check_vrf_status.find_vrf(
            'Lasers', vendor_specs['Cisco Nexus'], None, cisco_output)
    with open('tests/cmd_outputs/huawei_show_vrf.txt',
              'r', encoding='utf-8') as in_file:
        huawei_output = in_file.read()
    assert "not found" in check_vrf_status.find_vrf(
            'Galaxy', vendor_specs['Huawei CE'], None, huawei_output)
    assert "present" in check_vrf_status.find_vrf(
            'Lasers', vendor_specs['Huawei CE'], None, huawei_output)
