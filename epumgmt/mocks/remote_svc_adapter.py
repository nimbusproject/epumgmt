from state import WorkerInstanceState, EPUControllerState


class FakeRemoteSvcAdapter:

    def __init__(self):

        self.open_channel = False
        self.allow_initialize = True
        self.allow_controller_map = True
        self.fake_controller_map = {}
        self.fake_instances = []
        self.fake_worker_state = {}
        self.worker_state_raises = None

    def initialize(self, m, run_name, cloudinitd):
        if self.allow_initialize:
            self.open_channel = True

    def is_channel_open(self):
        return self.open_channel

    def controller_map(self, vms):

        if not self.allow_controller_map:
            return {}

        return self.fake_controller_map

    def worker_state(self, controllers, provisioner_vm):

        if self.worker_state_raises:
            raise self.worker_state_raises

        return self.fake_worker_state
