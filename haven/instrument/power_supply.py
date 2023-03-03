from ophyd import (
    Device,
    Component as Cpt,
    FormattedComponent as FCpt,
    EpicsSignal,
    EpicsSignalRO,
    EpicsMotor,
)

from .._iconfig import load_config
from .instrument_registry import registry


@registry.register
class NHQ203MChannel(Device):
    """A single channel on a controllable power supply."""

    ch_num: int

    # Device components
    potential = FCpt(
        EpicsSignal,
        name="potential",
        suffix="{prefix}:Volt{ch_num}_rbv",
        write_pv="{prefix}:SetVolt{ch_num}",
        tolerance=2,
    )
    current = FCpt(EpicsSignalRO, name="current", suffix="{prefix}:Curr{ch_num}_rbv")
    ramp_rate = FCpt(
        EpicsSignal,
        name="ramp_rate",
        suffix="{prefix}:RampSpeed{ch_num}",
        write_pv="{prefix}:RampSpeed{ch_num}_rbv",
    )
    status = FCpt(EpicsSignalRO, name="status", suffix="{prefix}:ModStatus{ch_num}_rbv")

    def __init__(self, prefix: str, ch_num: int, name: str, *args, **kwargs):
        self.ch_num = ch_num
        super().__init__(prefix=prefix, name=name, *args, **kwargs)


def load_power_supplies(config=None):
    if config is None:
        config = load_config()
    # Determine if any power supplies are available
    ps_configs = config.get("power_supply", {})
    for name, ps_config in ps_configs.items():
        # Do it once for each channel
        for ch_num in range(1, ps_config["n_channels"] + 1):
            this_name = f"{name}_ch{ch_num}"
            NHQ203MChannel(
                name=this_name,
                prefix=ps_config["prefix"],
                ch_num=ch_num,
                labels={"power_supplies"},
            )
