from pyantonlib.channel import DefaultProtoChannel
from pyantonlib.plugin import AntonPlugin
from anton.plugin_pb2 import PipeType

from pyantonlib.utils import log_info


class TestService(AntonPlugin):

    def setup(self, plugin_startup_info):
        self.channel = DefaultProtoChannel()
        registry = self.channel_registrar()
        registry.register_controller(PipeType.DEFAULT, self.channel)

    def on_start(self):
        pass

    def on_stop(self):
        pass
