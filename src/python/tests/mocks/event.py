
class Event:
    """ Fake event class for testing em_core
    """

    def __init__(self, name="", timestamp="", state=None, source="",
                 last_queuelen_size=None, de_state=None):
        self.name = name
        self.timestamp = timestamp
        self.source = source
        self.extra = {}
        if state:
            self.extra["state"] = state
        if last_queuelen_size:
            self.extra["last_queuelen_size"] = last_queuelen_size
        if de_state:
            self.extra["de_state"] = de_state
