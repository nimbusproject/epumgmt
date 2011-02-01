import os
from epumgmt.main import get_class_by_keyword, get_all_configs

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

class RunVM:
    """Object to store instance information.
    """

    # See the comment around the "service_type" variable below
    WORKER_SUFFIX = "-workervm"

    def __init__(self):

        # No IaaS awareness yet, assumes you start/stop with same conf.
        # TODO: this will be a blocker when multiple IaaS systems are in use by a system.
        # cloudinit.d itself will differentiate between multiple IaaS systems.
        self.instanceid = None

        # Assumed that harness can ssh to this node
        self.hostname = None

        # The haservice that caused this VM to be started.
        # If this VM was heard about from intaking an EPU controller's log
        # files (i.e., a worker VM for that EPU controller), then the value
        # will be that haservice name plus the constant WORKER_SUFFIX (see
        # above).
        self.service_type = None

        # Absolute path to the localhost directory of log files to look
        # for events that happened on this vm
        self.runlogdir = None

        # Absolute path to the log file directory on the VM to look for
        # events.
        self.vmlogdir = None

        # List of events that have parsed and recorded so far.
        self.events = []
