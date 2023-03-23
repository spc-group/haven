from bluesky import suspenders
from ophyd import FormattedComponent as FCpt, EpicsSignal
from apstools.devices.shutters import ApsPssShutterWithStatus

from .._iconfig import load_config
from .instrument_registry import registry


class Shutter(ApsPssShutterWithStatus):
    open_signal = FCpt(EpicsSignal, "{self.open_pv}")
    close_signal = FCpt(EpicsSignal, "{self.close_pv}")

    def __init__(self, close_pv, state_pv, *args, open_pv=None, **kwargs):
        """Either *open_pv* or *prefix* is a required keyword argument."""
        # Check for a valid open PV
        if open_pv is None:
            try:
                open_pv = kwargs.pop("prefix")
            except KeyError:
                raise TypeError(
                    "Shutter() requires either *open_pv* or *prefix* arguments"
                )
        # Save PVs and instantiate the parent class
        self.open_pv = open_pv
        self.close_pv = close_pv
        self.state_pv = state_pv
        super().__init__(prefix=self.open_pv, state_pv=self.state_pv, *args, **kwargs)


def load_shutters(config=None):
    if config is None:
        config = load_config()
    for name, d in config["shutter"].items():
        shutter = Shutter(
            open_pv=d["open_pv"],
            close_pv=d["close_pv"],
            state_pv=d["status_pv"],
            name=f"Shutter {name}",
            labels={"shutters"},
        )
        registry.register(shutter)
