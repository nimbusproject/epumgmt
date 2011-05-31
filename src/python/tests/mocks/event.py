
class Event:
    """ Fake event class for testing em_core
    """

    def __init__(self, name=None, timestamp=None, state=None):
        self.name = name
        self.timestamp = timestamp
        self.extra = {}
        self.extra["state"] = state
