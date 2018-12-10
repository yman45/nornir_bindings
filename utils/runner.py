import os
import os.path
import ipaddress
import click
from importlib import import_module
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError
from nornir.core import InitNornir
from nornir.plugins.functions.text import print_result
from utils.nornir_utils import nornir_set_credentials
from app_exception import AppException


class NoGroupsHost(AppException):
    '''Exception to raise in a process of adding host into inventory if there
    are no groups configured for that host.'''
    pass


class ConfigNotFound(AppException):
    '''Exception to raise if Nornir config is not founded on given path.'''
    pass


class CorruptedConfig(AppException):
    '''Exception to raise if there is a problem with Nornir config.'''
    pass


@click.command()
@click.option('-c', '--config', default='config.yml', metavar='<PATH>',
              help='path to Nornir config file')
@click.argument('hostname')
def main(config, hostname):
    '''Dynamically choose Nornir binding defind in 'bindings/' directory and
    execute it on HOSTNAME. If HOSTNAME is not in inventory, you will be
    prompted to add it in (follow instructions in prompts).
    '''
    try:
        check_config(config)
    except ConfigNotFound:
        click.echo('Config can not be found at {}'.format(config))
        exit(1)
    except CorruptedConfig as e:
        click.echo('Config error - {}'.format(e))
        exit(1)
    if not is_in_inventory(config, hostname):
        click.echo('Host not found in inventory.')
        click.confirm('Add it?', abort=True)
        txt1 = ('Enter IP address to put it in config or'
                ' domain name to do a DNS lookup into')
        ip_addr = click.prompt(txt1)
        try:
            host_defnintion = ipaddress.ip_address(ip_addr)
        except ValueError:
            try:
                import socket
                host_defnintion = socket.gethostbyname(hostname+'.'+ip_addr)
            except socket.gaierror:
                click.echo('Incorrect IP address, hostname or domain')
                exit(1)
        click.echo('Available groups: {}'.format(
            ', '.join([x for x in get_inventory_groups(config)])))
        txt2 = ('Enter groups separated by commas, spaces will'
                ' be stripped, unknown groups ignored, new groups creation'
                ' unsuppoted')
        groups = click.prompt(txt2)
        add_to_inventory(config, hostname, host_defnintion, groups)
    bindings = [x for x in os.listdir(
        'bindings') if '.py' in x and not x.startswith('.')]
    bindings_dict = {y: x for y, x in enumerate(bindings)}
    for num, binding in bindings_dict.items():
        click.echo('{}: {}'.format(num+1, binding[:-3]))
    input_num = click.prompt('Choose binding to run', type=int)
    chosen_binding = bindings_dict[input_num-1][:-3]
    binding_module = import_module('.'+chosen_binding, package='bindings')
    nrnr = InitNornir(config_file='config.yml')
    nrnr = nrnr.filter(name=hostname)
    nornir_set_credentials(nrnr)
    result = binding_module.execute(nrnr)
    print_result(result[hostname][0])


def get_inventory_groups(config):
    '''Parse Nornir config file to find group inventory file and parse it next.
    Grab all configured groups and return them.
    Arguments:
        * config - Nornir configuration file location
    Returns:
        view of dictionary keys, which represents groups defined in inventory
    '''
    yaml = YAML()
    with open(config, 'r', encoding='utf-8') as config_file:
        config_yaml = yaml.load(config_file)
    group_inventory = config_yaml['SimpleInventory']['group_file']
    with open(group_inventory, 'r', encoding='utf-8') as group_file:
        groups = yaml.load(group_file)
    return groups.keys()


def is_in_inventory(config, hostname):
    '''Initialize Nornir and check if hostname is defined in inventory.
    Argumets:
        * config - Nornir configuration file location
        * hostname - hostname that will be looked up
    Returns:
        * True or False - is host in inventory
    '''
    nrnr = InitNornir(config_file=config)
    if hostname not in nrnr.inventory.hosts.keys():
        return False
    else:
        return True


def add_to_inventory(config, hostname, ip, groups, no_such_group_ignore=False):
    '''Add host to Nornir inventory file. Raise NoGroupsHost exception if no
    groups configured, or all of them not exist (in keys of
    no_such_group_ignore flag is set).
    Arguments:
        * config - Nornir configuration file location
        * hostname - host name, that will be added into inventory
        * ip - host IP address (checking if it valid is out of scope of that
            function)
        * groups - string that represents groups this host will be added to;
            group names must be separated by commas, spaces will be ignored
        * no_such_group_ignore (default to False) - if True, silently drop
            unexisted groups, otherwise raise ValueError
    Returns nothing
    '''
    if not groups:
        raise NoGroupsHost('No groups configured')
    configured_groups = get_inventory_groups(config)
    groups = [x.strip() for x in groups.split(',')]
    cleaned_groups = []
    # we are going to use this for stripping nonexisiting groups if
    # no_such_group_ignore flag is set
    for group in groups:
        if group not in configured_groups:
            if not no_such_group_ignore:
                raise ValueError('Group {} is not configured'.format(group))
            else:
                continue
        else:
            cleaned_groups.append(group)
    if len(cleaned_groups) == 0:
        raise NoGroupsHost('All configured groups not exist')
    host = {hostname: {"nornir_host": ip, "groups": cleaned_groups}}
    yaml = YAML()
    with open(config, 'r', encoding='utf-8') as config_file:
        config_yaml = yaml.load(config_file)
    host_inventory = config_yaml['SimpleInventory']['host_file']
    yaml.indent(mapping=2, sequence=2, offset=2)
    with open(host_inventory, 'a', encoding='utf-8') as host_file:
        yaml.dump(host, host_file)


def check_config(config):
    '''Check Nornir config for existance and syntax. Raise exceptions if
    problem found.
    Arguments:
        * config - path to Nornir config
    Returns nothing
    '''
    if not os.path.isfile(config):
        raise ConfigNotFound('No config found at {}'.format(config))
    try:
        yaml = YAML()
        config = yaml.load(config)
        host_file = config['SimpleInventory']['host_file']
        group_file = config['SimpleInventory']['group_file']
        yaml.load(host_file)
        yaml.load(group_file)
    except ScannerError as e:
        raise CorruptedConfig('Corrupted config: {}'.format(e))


if __name__ == '__main__':
    main()
