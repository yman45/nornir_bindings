import getpass

def nornir_set_credentials(nornir, username=None):
    if not username:
        from os import getuid
        from pwd import getpwuid
        username = getpwuid(getuid())[0]
    password = getpass.getpass()
    for host in nornir.inventory.hosts.values():
        host.data["nornir_username"] = username
        host.data["nornir_password"] = password
