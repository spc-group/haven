import asyncio
import logging

from ophyd import Device, EpicsMotor
from ophyd import FormattedComponent as FCpt

from .._iconfig import load_config
from .device import aload_devices, make_device
from .instrument_registry import registry

__all__ = ["XYStage", "load_stages"]


log = logging.getLogger(__name__)


@registry.register
class XYStage(Device):
    """An XY stage with two motors operating in orthogonal directions.

    Vertical and horizontal are somewhat arbitrary, but are expected
    to align with the orientation of a camera monitoring the stage.

    Parameters
    ==========

    pv_vert
      The suffix to the PV for the vertical motor.
    pv_horiz
      The suffix to the PV for the horizontal motor.
    """

    vert = FCpt(EpicsMotor, "{prefix}{pv_vert}", labels={"motors"})
    horiz = FCpt(EpicsMotor, "{prefix}{pv_horiz}", labels={"motors"})

    def __init__(
        self,
        prefix: str,
        pv_vert: str,
        pv_horiz: str,
        labels={"stages"},
        *args,
        **kwargs,
    ):
        self.pv_vert = pv_vert
        self.pv_horiz = pv_horiz
        super().__init__(prefix, labels=labels, *args, **kwargs)


def load_stage_coros(config=None):
    """Provide co-routines for loading the stages defined in the
    configuration files.

    """
    if config is None:
        config = load_config()
    for name, stage_data in config.get("stage", {}).items():
        yield make_device(
            XYStage,
            name=name,
            prefix=stage_data["prefix"],
            pv_vert=stage_data["pv_vert"],
            pv_horiz=stage_data["pv_horiz"],
        )


def load_stages(config=None):
    """Load the XY stages defined in the config ``[stage]`` section."""
    asyncio.run(aload_devices(*load_stage_coros(config=config)))
