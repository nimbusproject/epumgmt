
class Event:
    """ Fake event class for testing em_core
    """

    def __init__(self, name="", timestamp="", state=None, source="",
                 de_state=None, iaas_id=None, node_id=None, public_ip=None):
        self.name = name
        self.timestamp = timestamp
        self.source = source
        self.extra = {}
        if state:
            self.extra["state"] = state
        if de_state:
            self.extra["de_state"] = de_state
        if public_ip:
            self.extra["public_ip"] = public_ip
        if iaas_id:
            self.extra["iaas_id"] = iaas_id
        if node_id:
            self.extra["node_id"] = node_id
