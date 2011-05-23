import logging
import string
import em_core_fetchkill

from epumgmt.api.exceptions import *
from epumgmt.api.actions import ACTIONS
from epumgmt.main import get_class_by_keyword, get_all_configs
from epumgmt.main import Modules
import epumgmt.main.em_args as em_args
import em_core_load
import em_core_eventgather
import em_core_findworkers
import em_core_logfetch
import em_core_persistence
import em_core_reconfigure
import em_core_status
import em_core_termination
import em_core_workloadtest


# -----------------------------------------------------------------------------
# CORE LOGIC (this is the whole program)
# -----------------------------------------------------------------------------

def core(opts, dbgmsgs=None):
    """Run epumgmt.
    
    From here 'down' there is no concept of a commandline program, only
    'args' which could be coming from any kind of protocol based request.
    
    To make such a thing, construct an opts object with the expected
    member names and values and pass it in to this method.
    
    See the 'em_args' module and the defaults 'Parameters' implementations to
    fully understand arg intake.  See the 'em_cmdline' module to see how args
    are taken in and how the result of the program (no exception or exception)
    is translated into a return code.
    """
    
    # -------------------------------------------------------------------------
    # SETUP Parameters
    #import epumgmt.defaults -------------------------------------------------------------------------
    
    if not opts:
        raise InvalidInput("No arguments")
        
    # in the default deployment, this is added by the .sh script wrapper 
    if not opts.conf:
        raise InvalidInput("The path to the 'main.conf' file is required, see --help.")
        
    ac = get_all_configs(opts.conf)
    
    p_cls = get_class_by_keyword("Parameters", allconfigs=ac)
    p = p_cls(ac, opts)

    # -------------------------------------------------------------------------
    # REQUIRED arguments
    # -------------------------------------------------------------------------
    
    # --conf is also required; already checked for above
    
    given_action = p.get_arg_or_none(em_args.ACTION)
    if not given_action:
        msg = "The %s argument is required, see -h" % em_args.ACTION.long_syntax
        raise InvalidInput(msg)
        
    action = validate_action(given_action)

    # -------------------------------------------------------------------------
    # Common
    # -------------------------------------------------------------------------
    
    c_cls = get_class_by_keyword("Common", allconfigs=ac)
    c = c_cls(p)

    # now there is a logger finally:
    if dbgmsgs:
        c.log.debug(dbgmsgs)

    try:
        _core(action, p, c)
    except:
        # Important for invocation logs to also record any problem
        c.log.exception("")
        raise
        
def _core(action, p, c):
        
    # -------------------------------------------------------------------------
    # INSTANTIATE the rest of the needed instances
    # -------------------------------------------------------------------------
    
    event_gather_cls = c.get_class_by_keyword("EventGather")
    event_gather = event_gather_cls(p, c)
    
    persistence = em_core_persistence.Persistence(p, c)

    runlogs_cls = c.get_class_by_keyword("Runlogs")
    runlogs = runlogs_cls(p, c)

    remote_svc_adapter_cls = c.get_class_by_keyword("RemoteSvcAdapter")
    remote_svc_adapter = remote_svc_adapter_cls(p, c)
    
    
    # -------------------------------------------------------------------------
    # VALIDATE
    # -------------------------------------------------------------------------
    
    # At least currently, this is required for all actions.
    run_name = p.get_arg_or_none(em_args.NAME)
    if not run_name:
        raise InvalidInput("The %s action requires run_name, see -h" % action)
    
    c.log.info("Validating '%s' action for '%s'" % (action, run_name))
    
    event_gather.validate()
    persistence.validate()
    runlogs.validate()
    remote_svc_adapter.validate()
    
    modules = Modules(event_gather, persistence, runlogs, remote_svc_adapter)
    
    # Always load from cloudinit.d initially
    c.log.debug("Loading the launch plan for '%s'" % run_name)
    cloudinitd = em_core_load.get_cloudinit(p, c, modules, run_name)

    # -------------------------------------------------------------------------
    # BRANCH on action
    # -------------------------------------------------------------------------
    
    if c.dryrun:
        c.log.info("Performing DRYRUN '%s' for '%s'" % (action, run_name))
    else:
        c.log.info("Performing '%s' for '%s'" % (action, run_name))

    if action == ACTIONS.LOAD:
        c.log.info("Load only, done.")
    elif action == ACTIONS.UPDATE_EVENTS:
        em_core_eventgather.update_events(p, c, modules, run_name)
    elif action == ACTIONS.KILLRUN:
        no_fetch = p.get_arg_or_none(em_args.KILLRUN_NOFETCH)
        try:
            if not no_fetch:
                em_core_findworkers.find_once(p, c, modules, run_name)
                em_core_logfetch.fetch_all(p, c, modules, run_name, cloudinitd)
        except KeyboardInterrupt:
            raise
        except Exception:
            c.log.exception("Fetch failed, moving on to terminate anyhow")
        em_core_termination.terminate(p, c, modules, run_name, cloudinitd)
    elif action == ACTIONS.LOGFETCH:
        em_core_logfetch.fetch_all(p, c, modules, run_name, cloudinitd)
    elif action == ACTIONS.FIND_WORKERS_ONCE:
        em_core_findworkers.find_once(p, c, modules, run_name)
    elif action == ACTIONS.FETCH_KILL:
        em_core_findworkers.find_once(p, c, modules, run_name)
        em_core_fetchkill.fetch_kill(p, c, modules, run_name, cloudinitd)
    elif action == ACTIONS.EXECUTE_WORKLOAD_TEST:
        em_core_workloadtest.execute_workload_test(p, c, modules, run_name)
    elif action == ACTIONS.GENERATE_GRAPH:
        try:
            import em_core_generategraph
        except ImportError:
            c.log.exception("")
            raise IncompatibleEnvironment("Problem with graphing dependencies: do you have "
            "matplotlib installed? (matplotlib is the source of the 'pylab' module)")
        em_core_generategraph.generate_graph(p, c, modules, run_name)
    elif action == ACTIONS.RECONFIGURE_N:
        em_core_reconfigure.reconfigure_n(p, c, modules, run_name, cloudinitd)
    elif action == ACTIONS.STATUS:

        # These parsable reports are not ready yet
        instance_report = p.get_arg_or_none(em_args.REPORT_INSTANCE)
        service_report = p.get_arg_or_none(em_args.REPORT_SERVICE)
        if instance_report and service_report:
            both = em_args.REPORT_INSTANCE.long_syntax + " and " + em_args.REPORT_SERVICE.long_syntax
            raise InvalidInput("You may only choose one status report option at a time, you choose both %s" % both)
        if instance_report:
            pass
        elif service_report:
            pass
        else:
            em_core_status.pretty_status(p, c, modules, run_name, cloudinitd)
    else:
        raise ProgrammingError("unhandled action %s" % action)


# -----------------------------------------------------------------------------
# GLOBAL VALIDATIONS
# -----------------------------------------------------------------------------

def validate_action(action):
    action = string.strip(action)
    action = string.lower(action)
    if not action:
        raise InvalidInput("action is missing/empty")
                          
    if action not in ACTIONS().all_actions():
        raise InvalidInput("Unknown action: '%s'" % action)
        
    return action


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

control_args = {}
for k in em_args.ALL_EC_ARGS_LIST:
    control_args[k.name] = k

class EPUMgmtOpts(object):

    def __init__(self, name=None, conf_file=None, cmd_opts=None):
        """
Create an option set. All parameters are default except for
the mandatory ones which are required to create the object.

Alternatively the values in this object can be populated with a
command line option parsed structure.
"""
        # create a dictionary of command line options.
        self.conf = conf_file
        self.name = name

        if cmd_opts:
            for k in control_args:
                ca = control_args[k]
                ca.value = cmd_opts.__dict__[k]

        if self.conf is None:
            msg = "The conf_file argument is required"
            raise InvalidInput(msg)
        if self.name is None:
            msg = "The name argument is required"
            raise InvalidInput(msg)

    def __setattr__(self, name, value):
        if name not in control_args:
            raise InvalidInput("No such option %s" % name)
        ca = control_args[name]
        ca.value = value

    def __getattr__(self, name):
        if name not in control_args:
            raise InvalidInput("No such option %s" % name)
        ca = control_args[name]
        return ca.value

class EPUMgmtAction(object):

    def __init__(self, opts):
        ac = get_all_configs(opts.conf)

        p_cls = get_class_by_keyword("Parameters", allconfigs=ac)
        self.p = p_cls(ac, opts)

        c_cls = get_class_by_keyword("Common", allconfigs=ac)
        self.c = c_cls(self.p)

        event_gather_cls = self.c.get_class_by_keyword("EventGather")
        event_gather = event_gather_cls(self.p, self.c)

        persistence = em_core_persistence.Persistence(self.p, self.c)

        runlogs_cls = self.c.get_class_by_keyword("Runlogs")
        runlogs = runlogs_cls(self.p, self.c)

        remote_svc_adapter_cls = self.c.get_class_by_keyword("RemoteSvcAdapter")
        remote_svc_adapter = remote_svc_adapter_cls(self.p, self.c)

        event_gather.validate()
        persistence.validate()
        runlogs.validate()
        remote_svc_adapter.validate()

        self.m = Modules(event_gather, persistence, runlogs, remote_svc_adapter)

    def set_logfile(self, fname):

        self.c.log = logging.getLogger("epu_test_logger")

        # TODO: fname

    def load(self, runname):
        return em_core_load.load(self.p, self.c, self.m, runname)

    def update(self, runname):
        return em_core_eventgather.update_events(self.p, self.c, self.m, runname)

    def kill(self, runname, cloudinitd):
        try:
            em_core_findworkers.find_once(self.p, self.c, self.m, runname)
            em_core_logfetch.fetch_all(self.p, self.c, self.m, runname, cloudinitd)
        except KeyboardInterrupt:
            raise
        except Exception:
            self.c.log.exception("Fetch failed, moving on to terminate anyhow")
        return em_core_termination.terminate(self.p, self.c, self.m, runname, cloudinitd)

    #def fetch_kill(self, runname):
    # em_core_findworkers.find(self.p, self.c, self.m, ACTIONS.FETCH_KILL, runname, once=True)
    # em_core_fetchkill.fetch_kill(self.p, self.c, self.m, runname)

    def logfetch(self, runname):
        return em_core_logfetch.fetch_all(self.p, self.c, self.m, runname)

    def findworkers(self, runname):
        return em_core_findworkers.find_once(self.p, self.c, self.m, ACTIONS.FIND_WORKERS_ONCE, runname)


