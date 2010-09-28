"""Entry points to epucontrol

cmdline -- This consumes system commandline arguments.  Provides argument
parsing and "--help" style text for a caller.  Translates exceptions into
process return codes.

main -- This drives the logic of the entire program.  Individual ecmodules
are loaded and invoked here.  For a definition of 'ecmodule' see api 
documentation (epucontrol/api/__init__.py).  This code may never interact
with anything but the interfaces defined there (the wcmodules).  "main" could
itself be a zope.interface in the future but it is not currently.

tests -- Programmatically drives various 'main' requests with real or mock
ecmodules. See epucontrol/mocks/__init__.py.  
Nose testing is used (easy_install nose).
"""

__all__ = ["get_class_by_keyword", "get_all_configs", "ACTIONS", "ControlArg"]

import ConfigParser
import os
import string

from epucontrol.api.exceptions import InvalidConfig, ProgrammingError

# See api/TODO.xt
#from workspacecontrol.api import interfacesdict

class Modules:
    def __init__(self, event_gather, iaas, persistence, runlogs, services):
        self.event_gather = event_gather
        self.iaas = iaas
        self.persistence = persistence
        self.runlogs = runlogs
        self.services = services

class ACTIONS:
    
    CREATE = "create"
    FETCH_KILL = "fetchkill"
    FIND_WORKERS = "find-workers"
    FIND_WORKERS_ONCE = "find-workers-once"
    KILLRUN = "killrun"
    LOGFETCH = "logfetch"
    STATUS = "status"
    UPDATE_EVENTS = "update-events"
    
    def all_actions(self):
        """Return the values of all Python members of this class whose
        identifiers are capitalized. So if you add an action, make sure
        to follow suit.
        """
        action_list = []
        for item in dir(self):
            if item == item.upper():
                action_list.append(getattr(self, item))
        return action_list


# -----------------------------------------------------------------------------
# "DEPENDENCY INJECTION"
# -----------------------------------------------------------------------------

def get_class_by_keyword(keyword, allconfigs=None, implstr=None):
    if not implstr and not allconfigs:
        raise ProgrammingError("get_class_by_keyword() needs one or the other: 'allconfigs' or 'implstr'")
    
    # See api/TODO.txt
    ## find the "fully qualified name" of the interface
    #if not interfacesdict.has_key(keyword):
    #    raise ProgrammingError("Unknown interface: '%s'" % keyword)
    
    # See api/TODO.txt
    ## get interface class so we can test the implementation class against it
    #i = get_class(interfacesdict[keyword])
    #if not i:
    #    raise ProgrammingError("Cannot load interface for '%s'" % keyword)
    
    # get the configured implementation class
    if not implstr:
        implstr = allconfigs.get("ecimpls", keyword)
    c = get_class(implstr)
    if not c:
        raise InvalidConfig("Cannot find implementation class: '%s'" % implstr)
      
    # See api/TODO.txt
    ## test impl class, assumes it is a zope.interface instance
    #if not i.implementedBy(c):
    #    raise ProgrammingError("Implementation '%s' does NOT implement the interface '%s'" % (c, i))
        
    return c

# See: http://stackoverflow.com/questions/
# 452969/does-python-have-an-equivalent-to-java-class-forname/452981#452981
def get_class( kls ):
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)            
    return m


# -----------------------------------------------------------------------------
# CONFIG 
# -----------------------------------------------------------------------------

def get_all_configs(mainconf_file_path):
    """Return RawConfigParser instantiated from supplied config source.
    
    Expecting "otherconfs" section in this file which has a list of paths to
    conf files which will be folded in to the config object.
    """
    if not os.path.isabs(mainconf_file_path):
        raise InvalidConfig("main.conf needs to be an absolute path, you provided '%s'" % mainconf_file_path)
        
    resolvedir = os.path.dirname(mainconf_file_path)
    mainconfig = _get_one_config(mainconf_file_path)
    otherconfs = mainconfig.options("otherconfs")
    
    for keyword in otherconfs:
        path = mainconfig.get("otherconfs", keyword)
        if not os.path.isabs(path):
            path = os.path.join(resolvedir, path)
        # if existing config object is passed in, new confs will be added
        _get_one_config(path, config=mainconfig)
    
    return mainconfig

def _get_one_config(filepath, config=None):
    if not filepath:
        raise InvalidConfig("filepath was not supplied to _get_one_config()")
    if not config:
        config = ConfigParser.RawConfigParser()
    config.read(filepath)
    return config


# -----------------------------------------------------------------------------
# Arg classes 
# -----------------------------------------------------------------------------

class ControlArg:
    
    def __init__(self, name, short_syntax, noval=False, since=None, deprecated=False, createarg=True, metavar=None):
        """Long syntax is always "--" + name
        
        short_syntax may be None
        
        If 'noval' is True, this is an arg that, if present, will trigger the
        value to be 'True', otherwise 'False'.  i.e., "was the flag present."
        Otherwise, it is presumed a string intake arg
        
        createarg -- Most of the arguments are for the create action. Use a
        False createarg so they are grouped differently from the create args
        
        if no metavar (see ec_optparse), metavar is capitalization of name
        """
        if not name:
            raise Exception("no arg name")
            
        self.name = name
        self.dest = name
        if not since:
            self.since = "v1"
        else:
            self.since = "v%s" % since
        self.short_syntax = short_syntax
        self.long_syntax = "--" + name
        self.help = None
        self.boolean = noval
        self.string = not noval
        self.deprecated = deprecated
        self.createarg = createarg
        self.metavar = metavar
        if not metavar:
            self.metavar = string.upper(name)
    
    def __repr__(self):
        return "ControlArg: %s" % self.name
