
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

class FakeCommon():
    """FakeCommon fakes the common object so we can check what
       gets logged by the stuff that calls it
    """


    def __init__(self):

        self.log = FakeLog()
