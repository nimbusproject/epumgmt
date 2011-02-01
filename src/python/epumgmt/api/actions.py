class ACTIONS:

    EXECUTE_WORKLOAD_TEST = "execute-workload-test"
    FETCH_KILL = "fetchkill"
    FIND_WORKERS_ONCE = "find-workers"
    GENERATE_GRAPH = "generate-graph"
    KILLRUN = "killrun"
    LOAD = "load"
    LOGFETCH = "logfetch"
    UPDATE_EVENTS = "update-events"

    # For later:
    #STATUS = "worker-status"

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
