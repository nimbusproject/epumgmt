from common import DefaultCommon
from parameters import DefaultParameters
from iaas import DefaultIaaS
from services import DefaultServices
from runlogs import DefaultRunlogs

class RunVM:
    """Object to store instance information.
    """
    
    def __init__(self):
        self.instanceid = None
        self.hostname = None
        self.runlogdir = None
        self.events = []
