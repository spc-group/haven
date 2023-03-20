from bluesky import suspenders
from ophyd import FormattedComponent as FCpt, EpicsSignal
from apstools.devices.shutters import ApsPssShutterWithStatus

from .._iconfig import load_config
from .instrument_registry import registry


class Shutter(ApsPssShutterWithStatus):
    open_signal = FCpt(EpicsSignal, "{self.open_pv}")
    close_signal = FCpt(EpicsSignal, "{self.close_pv}")

    def __init__(self, open_pv, close_pv, state_pv, *args, **kwargs):
        self.open_pv = open_pv
        self.close_pv = close_pv
        self.state_pv = state_pv
        super().__init__(prefix=self.open_pv, state_pv=self.state_pv, *args, **kwargs)


# A list of suspenders that will get populated once the shutters get loaded
shutter_suspenders = []


def load_shutters(config=load_config()):
    for name, d in config["shutter"].items():
        shutter = Shutter(
            open_pv=d["open_pv"],
            close_pv=d["close_pv"],
            state_pv=d["status_pv"],
            name=f"Shutter {name}",
            labels={"shutters"},
        )
        registry.register(shutter)
