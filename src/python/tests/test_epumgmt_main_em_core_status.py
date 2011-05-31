import epumgmt.main.em_core_status
import mocks.event

class TestStatus:
    import epumgmt.api

    def setup(self):
        # Old-style Worker
        self.testvm0 = epumgmt.api.RunVM()
        self.testvm0_nodeid = "id0"
        self.testvm0.nodeid = self.testvm0_nodeid
        self.testvm0_instanceid = "i-xxxxxxx"
        self.testvm0.instanceid = self.testvm0_instanceid
        self.testvm0_service_type = "vmvm" + epumgmt.api.RunVM.WORKER_SUFFIX
        self.testvm0.service_type = self.testvm0_service_type

        # New-style Worker
        self.testvm1 = epumgmt.api.RunVM()
        self.testvm1_nodeid = "id1"
        self.testvm1.nodeid = self.testvm1_nodeid
        self.testvm1_instanceid = "i-yyyyyyy"
        self.testvm1.instanceid = self.testvm1_instanceid
        self.testvm1.service_type = "whatev"
        self.testvm1_parent = "fake"
        self.testvm1.parent = self.testvm1_parent

        # Service
        self.testvm2 = epumgmt.api.RunVM()
        self.testvm2_nodeid = "id2"
        self.testvm2.nodeid = self.testvm2_nodeid
        self.testvm2_instanceid = "i-jjjjjjjj"
        self.testvm2.instanceid = self.testvm2_instanceid
        self.testvm2.service_type = "whatev"

        self.allvms = [self.testvm0, self.testvm1, self.testvm2]

        # VM with no events
        self.vm_no_events = epumgmt.api.RunVM()

        # VM with no iaas_state events
        self.vm_no_state_events = epumgmt.api.RunVM()
        events = [mocks.event.Event(name="fake", timestamp=1000)]
        self.vm_no_state_events.events = events

        # VM with one iaas_state event
        self.vm_one_state_event = epumgmt.api.RunVM()
        self.vm_one_state_event_state = "fake"
        events = [mocks.event.Event(name="iaas_state", timestamp=1000, state=self.vm_one_state_event_state)]
        self.vm_one_state_event.events = events

        # VM with two iaas_state events
        self.vm_two_state_events = epumgmt.api.RunVM()
        self.vm_two_state_events_state0 = "fakestarting"
        self.vm_two_state_events_state1 = "fakerunning"
        events = [mocks.event.Event(name="iaas_state", timestamp=1000, state=self.vm_two_state_events_state0),
                  mocks.event.Event(name="iaas_state", timestamp=2000, state=self.vm_two_state_events_state1)]
        self.vm_two_state_events.events = events

    def test_get_vm_with_nodeid(self):
        get_vm_with_nodeid = epumgmt.main.em_core_status._get_vm_with_nodeid
        got_vm = get_vm_with_nodeid(self.testvm0_nodeid, self.allvms)
        assert got_vm == self.testvm0

        got_vm = get_vm_with_nodeid("fake", self.allvms)
        assert got_vm == None

    def test_get_vm_with_instanceid(self):
        get_vm_with_instanceid = epumgmt.main.em_core_status._get_vm_with_instanceid
        got_vm = get_vm_with_instanceid(self.testvm1_instanceid, self.allvms)
        assert got_vm == self.testvm1

        got_vm = get_vm_with_instanceid("fake", self.allvms)
        assert got_vm == None

    def test_filter_out_workers(self):
        filter_out_workers = epumgmt.main.em_core_status._filter_out_workers
        nonworkers = filter_out_workers(self.allvms)

        assert not self.testvm0 in nonworkers
        assert not self.testvm1 in nonworkers
        assert self.testvm2 in nonworkers

    def test_filter_out_services(self):
        filter_out_services = epumgmt.main.em_core_status._filter_out_services
        workers = filter_out_services(self.allvms)

        assert self.testvm0 in workers
        assert self.testvm1 in workers
        assert not self.testvm2 in workers


    def test_find_state_from_events(self):
        find_state_from_events = epumgmt.main.em_core_status._find_state_from_events

        novm = find_state_from_events(None)
        assert novm == None

        novm = find_state_from_events(self.vm_no_events)
        assert novm == None

        novm = find_state_from_events(self.vm_no_state_events)
        assert novm == None

        state = find_state_from_events(self.vm_one_state_event)
        assert state == self.vm_one_state_event_state

        state = find_state_from_events(self.vm_two_state_events)
        assert state == self.vm_two_state_events_state1

