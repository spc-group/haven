"""A PyDM data plugin that uses an Ophyd registry object to
communicate with signals.

Provides funcitonality so that PyDM channels can be addressed as e.g.
``haven://mirror.pitch.user_readback``

"""

from typhos.plugins.core import SignalConnection, SignalPlugin

from haven import registry


class HavenConnection(SignalConnection):
    def __init__(self, channel, address, protocol=None, parent=None):
        # Create base connection
        super(SignalConnection, self).__init__(
            channel, address, protocol=protocol, parent=parent
        )
        self._connection_open = True
        self.signal_type = None
        self.is_float = False
        # Collect our signal
        self.signal = registry.find(address)
        # Subscribe to updates from Ophyd
        self.value_cid = self.signal.subscribe(
            self.send_new_value,
            event_type=self.signal.SUB_VALUE,
        )
        self.meta_cid = self.signal.subscribe(
            self.send_new_meta,
            event_type=self.signal.SUB_META,
        )
        # Add listener
        self.add_listener(channel)


class HavenPlugin(SignalPlugin):
    protocol = "haven"
    connection_class = HavenConnection
