import os
import sys
import traceback

class FakeLog():

    def __init__(self):
        self.transcript = []

    def info(self, msg, substitution=()):
        self.transcript.append(("INFO", msg % substitution))

    def debug(self, msg, substitution=()):
        self.transcript.append(("DEBUG", msg % substitution))

    def warn(self, msg, substitution=()):
        self.transcript.append(("WARNING", msg % substitution))

    def error(self, msg, substitution=()):
        self.transcript.append(("ERROR", msg % substitution))

    def exception(self, msg, substitution=()):
        exc = sys.exc_info()
        msg += "".join(traceback.format_exception(exc[0], exc[1], exc[2]))
        self.transcript.append(("ERROR", msg % substitution))

class FakeCommon():
    """FakeCommon fakes the common object so we can check what
       gets logged by the stuff that calls it
    """


    def __init__(self, p=None):

        self.log = FakeLog()
        self.trace = False
        self.p = p

    def resolve_var_dir(self, dir):

        return os.path.join(self.p.get_conf_or_none("ecdirs", "var"), dir)
