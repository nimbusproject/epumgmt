import sys
import traceback

class FakeLog():

    def __init__(self):
        self.transcript = []

    def info(self, msg):
        self.transcript.append(("INFO", msg))

    def debug(self, msg):
        self.transcript.append(("DEBUG", msg))

    def warn(self, msg):
        self.transcript.append(("WARNING", msg))

    def error(self, msg):
        self.transcript.append(("ERROR", msg))

    def exception(self, msg):
        exc = sys.exc_info()
        msg += "".join(traceback.format_exception(exc[0], exc[1], exc[2]))
        self.transcript.append(("ERROR", msg))

class FakeCommon():
    """FakeCommon fakes the common object so we can check what
       gets logged by the stuff that calls it
    """


    def __init__(self, p=None):

        self.log = FakeLog()
        self.trace = False
        self.p = p
