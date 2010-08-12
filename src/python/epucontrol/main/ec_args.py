from epucontrol.main import ACTIONS, ControlArg

a = []
ALL_EC_ARGS_LIST = a

################################################################################
# EC ARGUMENTS
#
# The following cmdline arguments may be queried via Parameters, using either
# the 'name' as the argument or simply the object like:
#   
#   params.get_arg_or_none(ec_args.GRACE_PERIOD)
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
#a.append(DRYRUN)
DRYRUN.help = "Do as little real things as possible, will still affect filesystem, for example logs and information persistence. (not implemented yet)"

NAME = ControlArg("name", "-n", metavar="RUN_NAME", createarg=False)
a.append(NAME)
NAME.help = "Unique run name for logs and management.  Can use across multiple invocations for launches that belong together."


################################################################################
# CREATE ARGS
################################################################################

GRACE_PERIOD = ControlArg("graceperiod", "-g", metavar="SEC")
a.append(GRACE_PERIOD)
GRACE_PERIOD.help = "Seconds to wait without success until the launch is considered unsuccessful. Default is infinity."

HASERVICE = ControlArg("haservice", "-s", metavar="NAME")
a.append(HASERVICE)
HASERVICE.help = "HA service to launch and validate"

IAAS_CONF = ControlArg("iaasconf", None, metavar="NAME")
#a.append(IAAS_CONF)
IAAS_CONF.help = "Override the iaas:confsection setting for this run.  See iaas.conf in the etc directory. (not implemented)"

JSON_VARS = ControlArg("jsonvars", "-j", metavar="PATH")
a.append(JSON_VARS)
JSON_VARS.help = "path to JSON containing variable names + values for template replacement, see services.conf for explanation"
