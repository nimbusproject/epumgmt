class IECError(Exception):
    """Generic exception; parent of all API exceptions.
    
    Every class/interface in the epucontrol.api package descends from
    IECModule, IECObject, or IECError.
    """
    
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class InvalidInput(IECError):
    """Exception for illegal/nonsensical commandline syntax/combinations.
    """
    
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class InvalidConfig(IECError):
    """Exception for misconfigurations.
    """
    
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class IncompatibleEnvironment(IECError):
    """Exception for when something has determined a problem with the
    deployment environment.
    """
    
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class UnexpectedError(IECError):
    """Exception for when a function/module cannot proceed.
    """
    
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class ProgrammingError(IECError):
    """Not listed in docstrings, should never be seen except during
    development.  An 'assert' device that can be propagated through the
    exception handling mechanisms just in case it is seen during deployment.
    """
    
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg
