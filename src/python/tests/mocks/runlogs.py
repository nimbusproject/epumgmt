
class FakeRunlogs:

    def __init__(self):

        self.vms = []

    def new_vm(self, vm):
        self.vms.append(vm)
