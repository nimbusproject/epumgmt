from cloudinitd.exceptions import ConfigException

class MockEPUClient(object):
    """Mock interface to the EPU service.

    """

    def __init__(self):

        self.alive = False

    def initialize(self, *args):

        self.alive = True

        
    def killrun(self):
        self._assert_alive()
        
        self.alive = False
        
    def _assert_alive(self):

        if not self.alive:
            raise IncompatibleEnvironment("EPU is no longer alive")


class DashiEPUClient(object):
    """Dashi interface to the EPU service.
    """

    from dashi import DashiConnection
    from dashi.bootstrap import DEFAULT_EXCHANGE

    provisioner_topic = "provisioner"

    def __init__(self, p, c):

        self.c = c
        self.p = p

    def initialize(self, m, run_name, cloudinitd):

        self.cloudinitd = cloudinitd
        self.provisioner_cid = self.cloudinitd.get_service("provisioner")
        
        amqp_server = self.provisioner_cid.get_attr_from_bag("broker_ip_address")
        try:
            amqp_port = self.provisioner_cid.get_attr_from_bag("broker_port")
        except ConfigException:
            amqp_port = "5672"
        amqp_username = self.provisioner_cid.get_attr_from_bag("rabbitmq_username")
        amqp_password = self.provisioner_cid.get_attr_from_bag("rabbitmq_password")
        amqp_exchange = None #TODO
        amqp_exchange = amqp_exchange or self.DEFAULT_EXCHANGE

        memory_name = self.p.get_conf_or_none("dashi", "memory_name")
        
        if memory_name:
            amqp_uri = "memory://%s" % memory_name
        else:
            amqp_uri = "amqp://%s:%s@%s/" % (
                        amqp_username,
                        amqp_password,
                        amqp_server,
                        )
        self.provisioner = self.DashiConnection(self.provisioner_topic,
                amqp_uri, amqp_exchange)

        self.alive = True


    def killrun(self):
        if not self.alive:
            self.c.log.error("EPU has already been shut down.")
            return

        self.provisioner.call("provisioner", "terminate_all")
        self.alive = False
