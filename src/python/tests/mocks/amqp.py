import BaseHTTPServer

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    
    def do_GET(self):
        self.send_response(200)

    def log_message(self, format, *args):
        pass

class FakeAMQPServer:
    """The FakeAMQPServer listens to requests, and OKs any get
    """

    def __init__(self):

        self.port = 8000
        self._server = BaseHTTPServer.HTTPServer(("", self.port), Handler)
        self._server.handle_request()
