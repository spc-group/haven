"""A PyDM data plugin that uses an Ophyd registry object to
communicate with signals.

Provides funcitonality so that PyDM channels can be addressed as e.g.
``haven://mirror.pitch.user_readback``

"""

from typhos.plugins.core import SignalConnection, SignalPlugin

from haven import registry


class HavenConnection(SignalConnection):
    def find_signal(self, address: str):
        """Find a signal in the registry given its address.
        This method is intended to be overridden by subclasses that
        may use a different mechanism to keep track of signals.
        Parameters
        ----------
        address
          The connection address for the signal. E.g. in
          "sig://sim_motor.user_readback" this would be the
          "sim_motor.user_readback" portion.
        Returns
        -------
        Signal
          The Ophyd signal corresponding to the address.
        """
        return registry[address]


class HavenPlugin(SignalPlugin):
    protocol = "haven"
    connection_class = HavenConnection
