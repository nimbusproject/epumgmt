class FakePersistence:

    def __init__(self):
        self.vm_store = {}

    def store_run_vms(self, run_name, vms):
        if not self.vm_store.has_key(run_name):
            self.vm_store[run_name] = []

        self.vm_store[run_name].extend(vms)

    def get_run_vms_or_none(self, run_name):
        return self.vm_store[run_name]

class FakeModules:
    
    def __init__(self, remote_svc_adapter=None, runlogs=None):

        self.remote_svc_adapter = remote_svc_adapter
        self.persistence = FakePersistence()
        self.runlogs = runlogs

def build_fake_scp_command_str(target, real_scp_command_str):
    def fake_scp_command_str(target, c, vm, cloudinitd):
        scpcmd = real_scp_command_str(c, vm, cloudinitd)
        scpcmd = "echo %s" % scpcmd
        return scpcmd
    
    return fake_scp_command_str

