from common import DefaultCommon
from parameters import DefaultParameters
from iaas import DefaultIaaS
from services import DefaultServices

class EPUVM:
    """Object to store instance information about what was launched
    by this harness.  Does not record what IaaS was used, currently
    the program makes simplifying assumption you're keeping all the
    EPU infrastructure isolated in one plcae (worker VMs are different).
    """
    
    def __init__(self):
        self.instanceid = None
        self.hostname = None
        