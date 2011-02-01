from epumgmt.api.actions import ACTIONS
import epumgmt.main.em_args as em_args
import epumgmt.main.em_core as em_core

import logging
import os

from epumgmt.api.exceptions import *
from epumgmt.main import get_class_by_keyword, get_all_configs
from epumgmt.main import Modules
import epumgmt.main.em_core_load as em_core_load
import epumgmt.main.em_core_eventgather as em_core_eventgather
import epumgmt.main.em_core_fetchkill as em_core_fetchkill
import epumgmt.main.em_core_findworkers as em_core_findworkers
import epumgmt.main.em_core_logfetch as em_core_logfetch
import epumgmt.main.em_core_persistence as em_core_persistence
import epumgmt.main.em_core_termination as em_core_termination

control_args = {}
for k in em_args.ALL_EC_ARGS_LIST:
    control_args[k.name] = k

def get_default_config():
    conf_file=os.path.join(os.environ['EPUMGMT_HOME'], "etc/epumgmt/main.conf")
    return conf_file

def get_default_ac():
    conf_file = get_default_config()
    ac = get_all_configs(conf_file)
    return ac

def get_parameters(opts, ac=None):
    if ac == None:
        ac = get_default_ac()
    p_cls = get_class_by_keyword("Parameters", allconfigs=ac)
    p = p_cls(ac, opts)
    return (p, ac)

def get_common(opts=None, p=None, ac=None):
    if p == None and opts == None:
        raise Exception("either opts of p must be specified")
    if ac == None:
        ac = get_default_ac()
    if p == None:
        (p, ac) = get_parameters(opts, ac)
    c_cls = get_class_by_keyword("Common", allconfigs=ac)
    c = c_cls(p)
    return (c, p, ac)


class EPUMgmtOpts(object):

    def __init__(self, name=None, conf_file=None, cmd_opts=None):
        """
        Create an option set.  All parameters are default except for
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

        if self.conf == None:
            msg = "The conf_file argument is required"
            raise InvalidInput(msg)
        if self.name == None:
            msg = "The name argument is required"
            raise InvalidInput(msg)

    def __setattr__(self, name, value):
        if name not in control_args:
            raise InvalidInput("No such option %s" % (name))
        ca = control_args[name]
        ca.value = value

    def __getattr__(self, name):
        if name not in control_args:
            raise InvalidInput("No such option %s" % (name))
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

        event_gather.validate()
        persistence.validate()
        runlogs.validate()

        self.m = Modules(event_gather, persistence, runlogs)

    def set_logfile(self, fname):

        self.c.log = logging.getLogger("epu_test_logger")

    def load(self, runname):
        return em_core_load.load(self.p, self.c, self.m, runname)

    def update(self, runname):
        return em_core_eventgather.update_events(self.p, self.c, self.m, runname)

    def kill(self, runname):
        try:
            em_core_findworkers.find(self.p, self.c, self.m, ACTIONS.KILLRUN, runname, once=True)
            em_core_logfetch.fetch_all(self.p, self.c, self.m, runname)
        except KeyboardInterrupt:
            raise
        except:
            self.c.log.exception("Fetch failed, moving on to terminate anyhow")
        return em_core_termination.terminate(self.p, self.c, self.m, runname)


    #def fetch_kill(self, runname):
    #    em_core_findworkers.find(self.p, self.c, self.m, ACTIONS.FETCH_KILL, runname, once=True)
    #    em_core_fetchkill.fetch_kill(self.p, self.c, self.m, runname)

    def logfetch(self, runname):
        return em_core_logfetch.fetch_all(self.p, self.c, self.m, runname)

    def findworkers(self, runname, once=False):
        return em_core_findworkers.find(self.p, self.c, self.m, ACTIONS.FIND_WORKERS_ONCE, runname)

def epumgmt_run(opts, dbgmsgs=None):
    em_core.core(opts, dbgmsgs=dbgmsgs)

