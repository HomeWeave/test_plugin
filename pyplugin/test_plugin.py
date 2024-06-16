from threading import Thread
from socketserver import BaseRequestHandler, TCPServer, ThreadingMixIn

from pyantonlib.channel import DefaultProtoChannel
from pyantonlib.plugin import AntonPlugin
from anton.plugin_pb2 import PipeType

from pyantonlib.utils import log_info


class DelimitedChannel:

    def __init__(self, sock):
        self.sock = sock

    def read(self, size):
        buf = bytes()
        while size > 0:
            buf += self.sock.recv(min(1024, size))
            size -= len(buf)
        return buf

    def read_message(self):
        d = self.read(4)
        size = d[0] << 24 | d[1] << 16 | d[2] << 8 | d[3]
        return self.read(size)

    def send_message(self, obj):
        l = len(obj)
        buf = bytes([(l >> 24) & 0xFF, (l >> 16) & 0xFF, (l >> 8) & 0xFF,
                     (l) & 0xFF])
        buf += obj
        self.sock.sendall(buf)


class ThreadedTCPRequestHandler(BaseRequestHandler):

    def setup(self):
        self.server.service.handler = self
        self.channel = DelimitedChannel(self.request)

    def handle(self):
        data = self.channel.read_message()


class ThreadedTCPServer(ThreadingMixIn, TCPServer):

    def __init__(self, service, *args, **kwargs):
        self.service = service
        super().__init__(*args, **kwargs)


class DefaultProtoChannelImp(DefaultProtoChannel):

    def __init__(self, service):
        self.service = service

    def on_call_status(self, msg):
        self.service.request_handler.channel.send_message("call_status")
        self.service.request_handler.channel.send_message(
            msg.SerializeToString())


class TestService(AntonPlugin):

    def setup(self, plugin_startup_info):
        self.handler = None
        self.channel = DefaultProtoChannel()
        registry = self.channel_registrar()
        registry.register_controller(PipeType.DEFAULT, self.channel)
        self.server = ThreadedTCPServer(self, ("", 56789),
                                        ThreadedTCPRequestHandler)
        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True

    def on_start(self):
        self.server_thread.start()

    def on_stop(self):
        pass
