import base64
from threading import Thread, Lock
from uuid import uuid4
from ws4py.client.threadedclient import WebSocketClient

from pyantonlib.channel import DefaultProtoChannel
from pyantonlib.channel import AppHandlerBase, DeviceHandlerBase
from pyantonlib.plugin import AntonPlugin
from anton.plugin_pb2 import PipeType

from pyantonlib.utils import log_info


class TestEnvironmentClient(WebSocketClient):

    def __init__(self, port):
        super().__init__(f"ws://127.0.0.1:{port}")
        self.listener = None

    def receive_message(self, msg):
        if self.listener:
            self.listener(msg.data)


class TestChannel:

    def __init__(self, client):
        self.client = client
        self.client.listener = self.on_message
        self.waiters = {}
        self.waiter_lock = Lock()

        self.listeners = {}

    def on_message(self, msg):
        obj = json.loads(msg)

        with self.waiter_lock:
            callback = self.waiters.pop(obj["id"], None)
            if callback:
                callback(obj)
                return

        fn = self.listeners.get(obj["kind"], None)
        if fn:
            fn(obj)

    def query(self, kind, data, callback):
        id = uuid4()
        obj = {"type": kind, "data": base64.b64encode(data), "id": id}

        with self.waiter_lock:
            self.waiters[id] = callback

        self.client.send(obj)

    def send(self, kind, data):
        obj = {"type": kind, "data": base64.b64encode(data), "id": uuid4()}
        self.client.send(obj)

    def register(self, kind, callback):
        self.listeners[kind] = callback


class AppHandler(AppHandlerBase):

    def __init__(self, plugin_startup_info, service):
        super().__init__(plugin_startup_info)
        self.service = service


class DeviceHandler(DeviceHandlerBase):

    def __init__(self, service):
        super().__init__()
        self.service = service

    def handle_instruction(self, msg, responder):
        responder(CallStatus(code=Status.STATUS_OK, msg="OK."))
        self.service.channel.send("instruction", msg.SerializeToString())

    def handle_set_device_state(self, msg, responder):
        responder(CallStatus(code=Status.STATUS_OK, msg="OK."))
        self.service.channel.send("set_device_state", msg.SerializeToString())

    def device_state_updated(self, msg):
        state = DeviceState()
        state.ParseFromString(base64.b64decode(msg["data"]))
        self.send_device_state_updated(state)


class TestService(AntonPlugin):

    def setup(self, plugin_startup_info):
        self.test_server = TestEnvironmentClient(56789)
        self.test_server.connect()

        self.device_handler = DeviceHandler(self)
        self.app_handler = AppHandler(plugin_startup_info, self)
        self.channel = DefaultProtoChannel(self.device_handler,
                                           self.app_handler)

        self.test_channel = TestChannel(self.test_server)
        self.test_channel.register("device_state_updated",
                                   self.device_handler.device_state_updated)

        registry = self.channel_registrar()
        registry.register_controller(PipeType.DEFAULT, self.channel)

    def on_start(self):
        self.server_thread.start()

    def on_stop(self):
        pass
