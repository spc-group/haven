import asyncio
import logging

from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import FormattedComponent as FCpt

from .._iconfig import load_config
from .device import aload_devices, await_for_connection
from .instrument_registry import registry

log = logging.getLogger(__name__)


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


async def make_power_supply_device(prefix, name, ch_num):
    dev = NHQ203MChannel(
        name=name,
        prefix=prefix,
        ch_num=ch_num,
        labels={"power_supplies"},
    )
    try:
        await await_for_connection(dev)
    except TimeoutError as exc:
        msg = f"Could not connect to power supply: {name} ({prefix})"
        log.warning(msg)
    else:
        log.info(f"Created power supply: {name}")
        registry.register(dev)
        return dev


def load_power_supply_coros(config=None):
    if config is None:
        config = load_config()
    # Determine if any power supplies are available
    ps_configs = config.get("power_supply", {})
    for name, ps_config in ps_configs.items():
        # Do it once for each channel
        for ch_num in range(1, ps_config["n_channels"] + 1):
            yield make_power_supply_device(
                name=f"{name}_ch{ch_num}",
                prefix=ps_config["prefix"],
                ch_num=ch_num,
            )


def load_power_supplies(config=None):
    asyncio.run(aload_devices(*load_power_supply_coros(config=config)))
