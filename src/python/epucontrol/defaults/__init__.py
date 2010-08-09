from common import DefaultCommon
from parameters import DefaultParameters
from iaas import DefaultIaaS
from services import DefaultServices
from runlogs import DefaultRunlogs

# See the comment around the "service_type" variable below
WORKER_SUFFIX = "-workervm"

class RunVM:
    """Object to store instance information.
    """
    
    def __init__(self):
        
        # No IaaS awareness yet, assumes you start/stop with same conf
        self.instanceid = None
        
        # Assumed that harness can ssh to this node
        self.hostname = None
        
        # The "--haservice" name launch that caused this VM to be started.
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
