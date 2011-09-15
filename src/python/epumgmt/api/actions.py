class ACTIONS:

    EXECUTE_WORKLOAD_TEST = "execute-workload-test"
    FETCH_KILL = "fetchkill"
    FIND_VERSIONS = "find-versions"
    FIND_WORKERS_ONCE = "find-workers"
    GENERATE_GRAPH = "generate-graph"
    KILLRUN = "killrun"
    LOAD = "load"
    LOGFETCH = "logfetch"
    RECONFIGURE_N = "reconfigure-n"
    STATUS = "status"
    UPDATE_EVENTS = "update-events"
    TORQUE_LOGFETCH = "torque-logfetch"

    def all_actions(self):
        """Return the values of all Python members of this class whose
        identifiers are capitalized. So if you add an action, make sure
        to follow suit.
        """
        action_list = []
        for item in dir(self):
            if item == item.upper():
                action_list.append(getattr(self, item))
        return action_list
