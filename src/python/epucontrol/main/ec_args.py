import string
from epucontrol.main import ACTIONS

a = []
ALL_EC_ARGS_LIST = a

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


################################################################################
# EC ARGUMENTS
#
# The following cmdline arguments may be queried via Parameters, using either
# the 'name' as the argument or simply the object like:
#   
#   params.get_arg_or_none(ec_args.GRACEPERIOD)
# 
################################################################################

actionlist = str(ACTIONS().all_actions())
actionlist = actionlist[1:] # remove '['
actionlist = actionlist[:-1] # remove ']'
ACTION = ControlArg("action", "-a", createarg=False)
a.append(ACTION)
ACTION.help = "Action for the program to take: %s" % actionlist

CONF = ControlArg("conf", "-c", createarg=False, metavar="PATH")
a.append(CONF)
CONF.help = "Absolute path to main.conf.  Required (shell script adds the default)."

DRYRUN = ControlArg("dryrun", None, createarg=False, noval=True)
a.append(DRYRUN)
DRYRUN.help = "Do as little real things as possible, will still affect filesystem, for example logs and information persistence. (not implemented yet)"

NAME = ControlArg("name", "-n", metavar="RUN_NAME", createarg=False)
a.append(NAME)
NAME.help = "Unique run name for logs and management.  Can use across multiple invocations for launches that belong together."


################################################################################
# CREATE ARGS
################################################################################

GRACEPERIOD = ControlArg("graceperiod", "-g", metavar="SEC")
a.append(GRACEPERIOD)
GRACEPERIOD.help = "Seconds to wait without success until the launch is considered unsuccessful. Default is infinity."

HASERVICE = ControlArg("haservice", "-s", metavar="NAME")
a.append(HASERVICE)
HASERVICE.help = "HA service to launch and validate"

IAASCONF = ControlArg("iaasconf", None, metavar="NAME")
a.append(IAASCONF)
IAASCONF.help = "Override the iaas:confsection setting for this run.  See iaas.conf in the etc directory."


