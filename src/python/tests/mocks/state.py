
class State:

    def __init__(self, de_state=None, de_conf_report=None, last_queuelen_size=None,
                 capture_time=None):

        self.de_state = de_state
        self.de_conf_report = de_conf_report
        self.last_queuelen_size = last_queuelen_size
        self.last_queuelen_time = 0
        self.capture_time = capture_time


class WorkerInstanceState:

    def __init__(self, iaas_state=None, iaas_state_time=None, nodeid=None, 
                 heartbeat_state=None, heartbeat_time=None):
        
        self.iaas_state = iaas_state
        self.iaas_state_time = iaas_state_time
        self.nodeid = nodeid
        self.heartbeat_state = heartbeat_state
        self.heartbeat_time = heartbeat_time
