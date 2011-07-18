import epumgmt.main.em_core_status
import epumgmt.defaults.epustates as epustates
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
        self.testvm2.events = []
        self.testvm2_running_time = 3
        self.testvm2.events.append(mocks.event.Event(name="iaas_state",
                      timestamp=self.testvm2_running_time,
                      state=epustates.RUNNING))
        self.testvm2_terminated_time = 8
        self.testvm2.events.append(mocks.event.Event(name="iaas_state",
                      timestamp=self.testvm2_terminated_time,
                      state=epustates.TERMINATED))

        # VM with Controller
        self.controller = epumgmt.api.RunVM()
        self.controller_nodeid = "idx"
        self.controller.nodeid = self.controller_nodeid
        self.controller_instanceid = "i-pppppppp"
        self.controller.instanceid = self.controller_instanceid
        self.controller_source = "controller"
        self.controller.service_type = self.controller_source
        events = [mocks.event.Event(source=self.controller_source)]
        self.first_de_state_time = 50
        self.first_de_state = "great"
        self.second_de_state_time = 100
        self.second_de_state = "paranoid"
        self.first_last_queuelen_size_time = 60
        self.first_last_queuelen_size = 1
        self.second_last_queuelen_size_time = 200
        self.second_last_queuelen_size = 2
        events.append(mocks.event.Event(name="de_state",
                      timestamp=self.first_de_state_time,
                      state=self.first_de_state))
        events.append(mocks.event.Event(name="de_state",
                      timestamp=self.second_de_state_time,
                      state=self.second_de_state))
        events.append(mocks.event.Event(name="last_queuelen_size",
                      timestamp=self.first_last_queuelen_size_time,
                      last_queuelen_size=self.first_last_queuelen_size))
        events.append(mocks.event.Event(name="last_queuelen_size",
                      timestamp=self.second_last_queuelen_size_time,
                      last_queuelen_size=self.second_last_queuelen_size))
        self.controller.events = events

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

        # All VMs
        self.allvms = [self.testvm0, self.testvm1, self.testvm2,
                       self.controller]

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


    def test_get_vm_with_controller(self):
        get_vm_with_controller = epumgmt.main.em_core_status._get_vm_with_controller

        novm = get_vm_with_controller(None, [])
        assert novm == None

        vm = get_vm_with_controller(self.controller_source, self.allvms)
        assert vm == self.controller


    def test_latest_controller_state(self):
        from epumgmt.main.em_core_status import _latest_controller_state

        nostate, noqlen = _latest_controller_state(None)
        assert nostate == None
        assert noqlen == None

        nostate, noqlen = _latest_controller_state(self.vm_no_events)
        assert nostate == None
        assert noqlen == None

        state, qlen = _latest_controller_state(self.controller)
        assert state == self.second_de_state
        assert qlen == self.second_last_queuelen_size

        extra_state = "okay"
        extra_event = mocks.event.Event(name="de_state",
                                  timestamp=self.second_de_state_time + 10,
                                  de_state=extra_state)
        self.controller.events.append(extra_event)

        state, _ = _latest_controller_state(self.controller)
        assert state == extra_state


    def test_get_events_from_controller_state(self):
        from epumgmt.main.em_core_status import _get_events_from_controller_state
        from mocks.state import State
        from mocks.common import FakeCommon

        blank_state = State()
        got_event = _get_events_from_controller_state(blank_state, 
                                                      None, None, None, None)
        assert got_event == False

        common = FakeCommon()

        test_vm = epumgmt.api.RunVM()

        de_state = "test_state"
        controller = "test_controller"
        test_state = State(de_state=de_state, capture_time=0)
        got_event = _get_events_from_controller_state(test_state, test_vm, controller, True, common)
        
        assert got_event == True
        assert len(test_vm.events) == 1
        assert test_vm.events[0].source == controller
        assert test_vm.events[0].name == "de_state"

        # Reset events
        test_vm.events = []
        assert len(test_vm.events) == 0

        de_conf_report = "test_report"
        controller = "test_controller"
        test_state = State(de_conf_report=de_conf_report, capture_time=0)
        got_event = _get_events_from_controller_state(test_state, test_vm, controller, True, common)
        
        assert got_event == True
        assert len(test_vm.events) == 1
        assert test_vm.events[0].source == controller
        assert test_vm.events[0].name == "de_conf_report"

        # Reset events
        test_vm.events = []
        assert len(test_vm.events) == 0

        last_queuelen_size = 42
        controller = "test_controller"
        test_state = State(last_queuelen_size=last_queuelen_size, capture_time=0)
        got_event = _get_events_from_controller_state(test_state, test_vm, controller, True, common)
        
        assert got_event == True
        assert len(test_vm.events) == 1
        assert test_vm.events[0].source == controller
        assert test_vm.events[0].name == "last_queuelen_size"


    def test_get_events_from_wis(self):
        from epumgmt.main.em_core_status import _get_events_from_wis
        from mocks.state import WorkerInstanceState
        from mocks.common import FakeCommon

        blank_wis = WorkerInstanceState()
        got_event = _get_events_from_wis(blank_wis, None, None, None, None)
        assert got_event == False
        
        
        common = FakeCommon()
        controller = "test_controller"

        test_vm = epumgmt.api.RunVM()
        iaas_state = "fake_running"
        iaas_state_time = 42
        nodeid = "hellonode"
        fake_wis = WorkerInstanceState(iaas_state=iaas_state, iaas_state_time=iaas_state_time,
                                       nodeid=nodeid)
        got_event = _get_events_from_wis(fake_wis, test_vm, controller, True, common)

        assert got_event == True
        assert len(test_vm.events) == 1
        assert test_vm.events[0].name == "iaas_state"


        # Reset events
        test_vm.events = []
        assert len(test_vm.events) == 0
        
        heartbeat_state = "beating"
        heartbeat_time = 42
        nodeid = "imarealnode"
        fake_wis = WorkerInstanceState(heartbeat_state=heartbeat_state,
                                       heartbeat_time=heartbeat_time, nodeid=nodeid)
        got_event = _get_events_from_wis(fake_wis, test_vm, controller, True, common)

        assert got_event == True
        assert len(test_vm.events) == 1
        assert test_vm.events[0].name == "heartbeat_state"


    def test_find_latest_worker_status(self):
        from epumgmt.main.em_core_status import _find_latest_worker_status
        from epumgmt.api.exceptions import ProgrammingError
        from mocks.common import FakeCommon
        from mocks.modules import FakeModules
        from mocks.remote_svc_adapter import FakeRemoteSvcAdapter
        from mocks.state import EPUControllerState, WorkerInstanceState

        svc_adapter = FakeRemoteSvcAdapter()
        modules = FakeModules(remote_svc_adapter=svc_adapter)
        common = FakeCommon()

        svc_adapter.allow_initialize = False
        _find_latest_worker_status(common, modules, "", None, [])

        # Check that we've logged something to WARNING
        # Filter out WARNING log messages
        warnings = [warning for warning in common.log.transcript if warning[0] == "WARNING"]
        assert len(warnings) == 1
        warning = warnings[0]
        warning_msg = warning[1]
        assert warning_msg.find("no channel open") != -1


        # reset log transcript
        common.log.transcript = []

        svc_adapter.allow_initialize = True
        svc_adapter.allow_controller_map = False
        _find_latest_worker_status(common, modules, "", None, [])

        warnings = [warning for warning in common.log.transcript if warning[0] == "WARNING"]
        assert len(warnings) == 1
        warning = warnings[0]
        warning_msg = warning[1]
        assert warning_msg.find("no controllers are configured") != -1


        common.log.transcript = []
        svc_adapter.allow_controller_map = True       


        allvms = []

        empty_instance_0 = "P-77686559"
        empty_vm_0 = epumgmt.api.RunVM()
        empty_vm_0.instanceid = empty_instance_0
        empty_vm_0.nodeid = "1234"
        allvms.append(empty_vm_0)

        empty_instance_1 = "P-88033864"
        empty_vm_1 = epumgmt.api.RunVM()
        empty_vm_1.instanceid = empty_instance_1
        empty_vm_1.nodeid = "2345"
        allvms.append(empty_vm_1)

        empty_instance_2 = "i-6f54ea01"
        empty_vm_2 = epumgmt.api.RunVM()
        empty_vm_2.instanceid = empty_instance_2
        empty_vm_2.nodeid = "3456"
        allvms.append(empty_vm_2)

        controller_instance = "P-32182444"
        controller_name = 'epu_controller_sleeper1'
        controller_vm = epumgmt.api.RunVM()
        controller_vm.instanceid = controller_instance
        allvms.append(controller_vm)

        svc_adapter.fake_controller_map = {empty_instance_0: [],
                                           empty_instance_1: [],
                                           empty_instance_2: [],
                                           controller_instance: [controller_name]}


        # Test for failure when no provisioner is available
        try:
            _find_latest_worker_status(common, modules, "", None, [])
        except ProgrammingError:
            raised_programming_error = True
        assert raised_programming_error


        provisioner = epumgmt.api.RunVM()
        provisioner_service_type = "provisioner"
        provisioner.service_type = provisioner_service_type
        allvms.append(provisioner)

        controller_state = EPUControllerState()

        empty_wis_0 = WorkerInstanceState(instanceid=empty_instance_0, nodeid=empty_vm_0.nodeid)
        controller_state.instances.append(empty_wis_0)
        empty_wis_1 = WorkerInstanceState(instanceid=empty_instance_1, nodeid=empty_vm_1.nodeid)
        controller_state.instances.append(empty_wis_1)
        empty_wis_2 = WorkerInstanceState(instanceid=empty_instance_2, nodeid=empty_vm_2.nodeid)
        controller_state.instances.append(empty_wis_2)

        svc_adapter.fake_worker_state = {'epu_controller_sleeper1': controller_state}

        _find_latest_worker_status(common, modules, "", None, allvms)

        # make sure at least one vm added to persistence
        assert len(modules.persistence.vm_store) > 0
        for run_name in modules.persistence.vm_store.keys():
            for persisted_vm in modules.persistence.vm_store[run_name]:
                assert persisted_vm.parent == controller_name

    def test_find_state_from_events_not_yet_started(self):
        """Test for problems when status is called before epu is booted
        """
        from epumgmt.main.em_core_status import _find_latest_worker_status
        from mocks.common import FakeCommon
        from mocks.modules import FakeModules
        from mocks.remote_svc_adapter import FakeRemoteSvcAdapter

        svc_adapter = FakeRemoteSvcAdapter()
        modules = FakeModules(remote_svc_adapter=svc_adapter)
        common = FakeCommon()
        allvms = []

        provisioner = epumgmt.api.RunVM()
        provisioner.instanceid = "i-fsdfdsfds"
        provisioner_service_type = "provisioner"
        provisioner.service_type = provisioner_service_type
        allvms.append(provisioner)

        svc_adapter.fake_controller_map = {provisioner.instanceid: [provisioner]}

        worker_state_exception = Exception("Something broke!")
        svc_adapter.worker_state_raises = worker_state_exception
        _find_latest_worker_status(common, modules, "", None, allvms)

        warnings = [warning for warning in common.log.transcript if warning[0] == "WARNING"]
        _, last_warning = warnings[-1]
        assert last_warning.find("Unable to get worker state for controllers") != -1


    def test_update_worker_parents(self):
        from epumgmt.main.em_core_status import _update_worker_parents
        from epumgmt.api.exceptions import ProgrammingError
        from mocks.common import FakeCommon
        from mocks.modules import FakeModules
        from mocks.state import EPUControllerState, WorkerInstanceState


        controllers = []
        controller_state_map = {}
        allvms = []

        common = FakeCommon()
        modules = FakeModules()

        run_name = "test_run"

        controller_0 = "epu_controller_sleeper1"
        controllers.append(controller_0)

        controller_0_state = EPUControllerState()

        worker_0 = WorkerInstanceState()
        worker_0_nodeid = "x-qwertyuiop"
        worker_0.nodeid = worker_0_nodeid

        worker_0_vm = epumgmt.api.RunVM()
        worker_0_vm.nodeid = worker_0_nodeid

        controller_0_state.instances.append(worker_0)
        controller_state_map[controller_0] = controller_0_state

        # Test when there's WorkerInstance that doesn't appear in the list of VMs
        _update_worker_parents(common, modules, run_name, controllers, controller_state_map, allvms)
        warnings = [warning for warning in common.log.transcript if warning[0] == "WARNING"]
        assert len(warnings) > 0
        _, log_message = warnings[0]
        assert log_message.find("knows about worker we have no IaaS id for yet") != -1


        # Test the normal case
        allvms.append(worker_0_vm)
        _update_worker_parents(common, modules, run_name, controllers, controller_state_map, allvms)

        assert worker_0_vm.parent == controller_0
        assert modules.persistence.vm_store[run_name][0] == worker_0_vm


        # Test when the VM's parent isn't the controller that owns it
        worker_0_vm.parent = "some_other_controller"
        try:
            _update_worker_parents(common, modules, run_name, controllers, controller_state_map, allvms)
        except ProgrammingError:
            programming_error_raised = True

        assert programming_error_raised

        # Test for controllers being present in the controller_map, but not the
        # controller state map
        common.log.transcript = []
        _update_worker_parents(common, modules, run_name, controllers, {}, allvms)
        warnings = [warning for warning in common.log.transcript if warning[0] == "WARNING"]
        _, warning = warnings[-1]
        assert warning.find("in list of controllers, but no state available.") != -1


    def test_update_worker_states(self):
        from epumgmt.main.em_core_status import _update_worker_states
        from epumgmt.api.exceptions import ProgrammingError
        from mocks.common import FakeCommon
        from mocks.modules import FakeModules
        from mocks.state import EPUControllerState, WorkerInstanceState

        controllers = []
        controller_state_map = {}
        allvms = []

        common = FakeCommon()
        modules = FakeModules()
        
        run_name = "test_run"

        controller_0 = "epu_controller_sleeper1"
        controllers.append(controller_0)

        controller_0_state = EPUControllerState()

        worker_0 = WorkerInstanceState()
        worker_0_nodeid = "x-qwertyuiop"
        worker_0.nodeid = worker_0_nodeid
        worker_0.iaas_state = "running"
        worker_0.iaas_state_time = 1307136434

        worker_0_vm = epumgmt.api.RunVM()
        worker_0_vm.nodeid = worker_0_nodeid

        controller_0_state.instances.append(worker_0)
        controller_state_map[controller_0] = controller_0_state


        # Test when there's WorkerInstance that doesn't appear in the list of VMs
        _update_worker_states(common, modules, run_name, controllers, controller_state_map, allvms)
        warnings = [warning for warning in common.log.transcript if warning[0] == "WARNING"]
        assert len(warnings) > 0
        _, log_message = warnings[0]
        assert log_message.find("knows about worker we have no IaaS id for yet") != -1


        allvms.append(worker_0_vm)

        # Test standard case where the worker has one new event. 
        _update_worker_states(common, modules, run_name, controllers, controller_state_map, allvms)

        assert modules.persistence.vm_store[run_name][0] == worker_0_vm
        assert len(worker_0_vm.events) == 1

        # Test for controllers being present in the controller_map, but not the
        # controller state map
        common.log.transcript = []
        _update_worker_states(common, modules, run_name, controllers, {}, allvms)
        warnings = [warning for warning in common.log.transcript if warning[0] == "WARNING"]
        _, warning = warnings[-1]
        assert warning.find("in list of controllers, but no state available.") != -1


    def test_update_controller_states(self):
        from epumgmt.main.em_core_status import _update_controller_states
        from epumgmt.api.exceptions import ProgrammingError
        from mocks.common import FakeCommon
        from mocks.modules import FakeModules
        from mocks.state import EPUControllerState, WorkerInstanceState

        controller_state_map = {}
        controller_map = {}
        allvms = []

        common = FakeCommon()
        modules = FakeModules()

        run_name = "test-run"

        empty_0_instanceid = "P-xxxxxxx"
        empty_0_vm = epumgmt.api.RunVM()
        empty_0_vm.instanceid = empty_0_instanceid
        empty_1_instanceid = "P-yyyyyyy"
        empty_1_vm = epumgmt.api.RunVM()
        empty_1_vm.instanceid = empty_1_instanceid

        controller_0 = "epu_controller_sleeper1"
        controller_0_instanceid = "i-treetree"
        controller_0_vm = epumgmt.api.RunVM()
        controller_0_vm.instanceid = controller_0_instanceid

        controller_map[empty_0_instanceid] = []
        controller_map[empty_1_instanceid] = []
        controller_map[controller_0_instanceid] = [controller_0]

        # Test for vms being present in controller_map, but not allvms
        try:
            _update_controller_states(common, modules, run_name, controller_map, controller_state_map, allvms)
        except ProgrammingError:
            raised_programming_error = True

        assert raised_programming_error

        allvms.append(empty_0_vm)
        allvms.append(empty_1_vm)
        allvms.append(controller_0_vm)

        controller_0_state = EPUControllerState()
        controller_0_state.de_state = "state"
        controller_0_state.capture_time = 42424242

        controller_state_map[controller_0] = controller_0_state

        _update_controller_states(common, modules, run_name, controller_map, controller_state_map, allvms)

        assert modules.persistence.vm_store[run_name][0] == controller_0_vm
        assert len(controller_0_vm.events) == 1

        # Test for controllers being present in the controller_map, but not the
        # controller state map
        common.log.transcript = []
        _update_controller_states(common, modules, run_name, controller_map, {}, allvms)
        warnings = [warning for warning in common.log.transcript if warning[0] == "WARNING"]
        _, warning = warnings[-1]
        assert warning.find("in list of controllers, but no state available.") != -1


    def test_get_running_terminate_timestamps(self):
        get_running_terminate_timestamps = epumgmt.main.em_core_status._get_running_terminate_timestamps

        map = get_running_terminate_timestamps(self.allvms)

        vm2_running_time, vm2_terminated_time = map["i-jjjjjjjj"]
        assert vm2_running_time == self.testvm2_running_time
        assert vm2_terminated_time == self.testvm2_terminated_time
