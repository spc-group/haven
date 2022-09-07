from ophyd import sim, EpicsSignal, EpicsSignalRO, Kind
from ._iconfig import load_config


__all__ = ["Signal", "SignalRO"]


class SimulatedSignal(sim.SynSignal):
    """A signal that mimics epics signal interface, but is actually
    simulated.

    Intended for use when no pv_prefix is given in the config file.

    """

    _kind = Kind.normal
    _name = "SimulatedSignal"
    _parent = None
    _metadata = {}

    def __init__(self, read_pv, write_pv, *args, **kwargs):
        print(read_pv, write_pv)
        return super().__init__(*args, **kwargs)


class SimulatedSignalRO(sim.SynSignalRO):
    """A signal that mimics epics signal interface, but is actually
    simulated.

    Intended for use when no pv_prefix is given in the config file.

    """

    _kind = Kind.normal

    def __init__(self, read_pv, *args, **kwargs):
        return super().__init__(*args, **kwargs)


def _add__new__method(cls, read_pv=None, *args, **kwargs):
    use_epics = load_config()["beamline"]["is_connected"]
    if issubclass(cls, EpicsSignalRO):
        superclass = SimulatedSignalRO
    else:
        superclass = SimulatedSignal
    if use_epics:
        return EpicsSignal.__new__(read_pv, *args, **kwargs)
    else:
        kwargs.pop("_kind", None)
        return superclass.__new__(superclass, *args, **kwargs)


def connected_signal(cls):
    cls.__new__ = _add__new__method
    return cls


@connected_signal
class Signal(EpicsSignal):
    ...


@connected_signal
class SignalRO(EpicsSignalRO):
    ...
