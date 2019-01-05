import os
import os.path
import ipaddress
import click
from importlib import import_module
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError
from nornir import InitNornir
from nornir.plugins.functions.text import print_result
from utils.nornir_utils import nornir_set_credentials
from app_exception import AppException


class RunnerException(AppException):
    '''Top-level module exception for inheritance purposes.'''
    pass


class NoGroupsHost(RunnerException):
    '''Exception to raise in a process of adding host into inventory if there
    are no groups configured for that host.'''
    pass


class UnconfiguredGroup(RunnerException):
    '''This exception raised if group, which name user typed in, is not
    congiured.'''
    pass


class ConfigNotFound(RunnerException):
    '''Exception to raise if Nornir config is not founded on given path.'''
    pass


class CorruptedConfig(RunnerException):
    '''Exception to raise if there is a problem with Nornir config.'''
    pass


class IPRetrievalError(RunnerException):
    '''This exception raised if no IP address can be retrived for given
    hostname by any defined method.'''
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
        click.echo(e)
        exit(1)
    if not is_in_inventory(config, hostname):
        click.echo('Host not found in inventory.')
        click.confirm('Add it?', abort=True)
        txt1 = ('Enter IP address to put it in config or'
                ' domain name to do a DNS lookup into')
        ip_addr = click.prompt(txt1)
        try:
            host_ip = get_host_ip_address(ip_addr, hostname)
        except IPRetrievalError as e:
            click.echo(e)
            exit(1)
        click.echo('Available groups: {}'.format(
            ', '.join([x for x in get_inventory_groups(config)])))
        txt2 = ('Enter groups separated by commas, spaces will'
                ' be stripped, unknown groups ignored, new groups creation'
                ' unsuppoted')
        groups = click.prompt(txt2)
        try:
            add_to_inventory(config, hostname, host_ip, groups)
        except UnconfiguredGroup as e:
            click.echo(e)
            exit(1)
    bindings = [x for x in os.listdir(
        'bindings') if '.py' in x and not x.startswith(('.', '_'))]
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
    group_inventory = config_yaml['inventory']['options']['group_file']
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
            unexisted groups, otherwise raise UnconfiguredGroup
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
                raise UnconfiguredGroup('Group {} is not configured'.format(
                    group))
            else:
                continue
        else:
            cleaned_groups.append(group)
    if len(cleaned_groups) == 0:
        raise NoGroupsHost('All configured groups not exist')
    host = {hostname: {"hostname": ip, "groups": cleaned_groups}}
    yaml = YAML()
    with open(config, 'r', encoding='utf-8') as config_file:
        config_yaml = yaml.load(config_file)
    host_inventory = config_yaml['inventory']['options']['host_file']
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
        with open(config, 'r', encoding='utf-8') as config_file:
            configuration = yaml.load(config_file)
        hosts = configuration['inventory']['options']['host_file']
        groups = configuration['inventory']['options']['group_file']
        # test host and group files for syntax by loading them
        with open(hosts, 'r', encoding='utf-8') as host_file:
            yaml.load(host_file)
        with open(groups, 'r', encoding='utf-8') as group_file:
            yaml.load(group_file)
    except ScannerError as e:
        raise CorruptedConfig('Corrupted config: {}'.format(e))


def get_host_ip_address(user_input, hostname):
    '''Get host IP address. First try to convert user input into valid IP
    address. If it fails use that input as domain name and try DNS lookup. If
    that fails to - raise IPRetrievalError.
    Arguments:
        * user_input - input from user (we expect it to be either IP address or
            name of DNS domain
        * hostname - just a hostname
    Returns string, representing IP address
    '''
    try:
        return ipaddress.ip_address(user_input).compressed
    except ValueError:
        try:
            import socket
            return socket.gethostbyname(hostname+'.'+user_input)
        except socket.gaierror:
            raise IPRetrievalError('Incorrect IP address, hostname or domain')


if __name__ == '__main__':
    main()
