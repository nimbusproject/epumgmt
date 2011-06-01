
class FakeRemoteSvcAdapter:

    def __init__(self):

        self.open_channel = False
        self.allow_initialize = True
        self.controller_map = controller_map

    def initialize(self, m, run_name, cloudinitd):
        if self.allow_initialize:
            self.open_channel = True

    def is_channel_open(self):
        return self.open_channel
