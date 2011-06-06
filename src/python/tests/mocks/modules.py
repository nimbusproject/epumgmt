
class FakePersistence:

    def __init__(self):
        self.vm_store = []

    def store_run_vms(self, run_name, vms):
        self.vm_store.extend(vms)

class FakeModules:
    
    def __init__(self, remote_svc_adapter=None):

        self.remote_svc_adapter = remote_svc_adapter
        self.persistence = FakePersistence()
