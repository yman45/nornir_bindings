import getpass


def nornir_set_credentials(nornir, username=None):
    '''Iterate through hosts in inventory and assign them credentials. If no
    username provided it will be gathered from OS. Password will be prompted.
    Arguments:
        * nornir - instance of nornir.core.Nornir
        * username (defaults to None) - username to access network nodes
    '''
    if not username:
        from os import getuid
        from pwd import getpwuid
        username = getpwuid(getuid())[0]
    password = getpass.getpass()
    for host in nornir.inventory.hosts.values():
        host.username = username
        host.password = password
