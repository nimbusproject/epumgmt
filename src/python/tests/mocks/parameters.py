
class FakeParameters(object):

    def __init__(self):
        self.config = {}

    def set_conf(self, section, key, val):

        if not self.config.has_key(section):
            self.config[section] = {}

        self.config[section][key] = val

    def get_conf_or_none(self, section, key):

        try:
            return self.config[section][key]
        except KeyError:
            return None
