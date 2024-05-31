"""A PyDM data plugin that uses an Ophyd registry object to
communicate with signals.

Provides funcitonality so that PyDM channels can be addressed as e.g.
``haven://mirror.pitch.user_readback``

"""
import logging
import time

import numpy as np
from qtpy.QtCore import Qt
from ophyd import Signal
from typhos.plugins.core import SignalConnection, SignalPlugin

from haven import registry


logger = logging.getLogger(__name__)


class HavenConnection(SignalConnection):
    def find_signal(self, address: str) -> Signal:
        return registry.find(address)


class HavenPlugin(SignalPlugin):
    protocol = "haven"
    connection_class = HavenConnection
