class AppException(Exception):
    '''Global application exception to inherit other exceptions from.'''
    pass


class UnsupportedNOS(AppException):
    '''Indicate that method receive NOS type/version that is currently
    unsupported by it.'''
    pass
