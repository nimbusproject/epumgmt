import os
from epumgmt.main import get_class_by_keyword, get_all_configs

def get_default_config():
    try:
        prefix = os.environ['EPUMGMT_HOME']
    except KeyError:
        prefix = os.path.expanduser("~/.epumgmt")
    conf_file=os.path.join(prefix, "etc/main.conf")
    return conf_file

def get_default_ac():
    conf_file = get_default_config()
    ac = get_all_configs(conf_file)
    return ac

def get_parameters(opts, ac=None):
    if ac is None:
        ac = get_default_ac()
    p_cls = get_class_by_keyword("Parameters", allconfigs=ac)
    p = p_cls(ac, opts)
    return (p, ac)

def get_common(opts=None, p=None, ac=None):
    if p is None and opts is None:
        raise Exception("either opts of p must be specified")
    if ac is None:
        ac = get_default_ac()
    if p is None:
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

        # The EPU internal node ID of the instance
        self.nodeid = None

        # Assumed that harness can ssh to this node
        self.hostname = None

        # The svc that caused this VM to be started.
        self.service_type = None

        # If this node was launched by an EPU Controller, the controller service endpoint name
        self.parent = None

        # Absolute path to the localhost directory of log files to look
        # for events that happened on this vm
        self.runlogdir = None

        # Absolute path to the log file directory on the VM to look for
        # events.
        self.vmlogdir = None

        # List of events that have parsed and recorded so far.
        self.events = []

    def __repr__(self):
        repr = "RunVM: "
        repr += "instanceid: %s " % self.instanceid
        repr += "nodeid: %s " % self.nodeid
        repr += "hostname : %s " % self.hostname
        repr += "service_type: %s " % self.service_type
        repr += "parent: %s " % self.parent
        repr += "runlogdir: %s " % self.runlogdir
        repr += "vmlogdir: %s " % self.vmlogdir
        repr += "events: %s " % self.events
        return repr

class WorkerInstanceState:
    """Object to store worker instance information from an EPU Controller state query
    """
    def __init__(self):
        self.nodeid = None
        self.parent_controller = None
        self.iaas_state = None # string, epu.states.*
        self.iaas_state_time = -1 # seconds since epoch or -1
        self.heartbeat_state = None # string, epu.epucontroller.health.NodeHealthState.*
        self.heartbeat_time = -1 # seconds since epoch or -1

class EPUControllerState:
    """Object to store a new EPU Controller information capture
    """

    def __init__(self):
        # Time when this set of data was fetched
        self.capture_time = -1 # seconds since epoch or -1

        # Actual controller service endpoint name
        self.controller_name = None

        self.de_state = None # stable engine or not - (a decision engine is not required to implement this)
        self.de_conf_report = None # Configuration report - (a decision engine is not required to implement this)

        # List of WorkerInstanceState
        self.instances = []

    def __repr__(self):
        repr = "EPUControllerState: "
        repr += "capture_time: '%s' " % self.capture_time
        repr += "controller_name: '%s' " % self.controller_name
        repr += "de_state: '%s' " % self.de_state
        repr += "de_conf_report: '%s' " % self.de_conf_report
        repr += "instances: '%s' " % self.instances

        return repr
