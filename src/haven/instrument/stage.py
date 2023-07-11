import logging

from ophyd import Device, FormattedComponent as FCpt, EpicsMotor

from .instrument_registry import registry
from .._iconfig import load_config
from .device import await_for_connection


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


async def make_stage_device(
    name: str,
    prefix: str,
    pv_vert: str,
    pv_horiz: str,
):
    stage = XYStage(prefix, name=name, pv_vert=pv_vert, pv_horiz=pv_horiz)
    try:
        await await_for_connection(stage)
    except TimeoutError as exc:
        msg = f"Could not connect to stage: {name} ({prefix})"
        log.warning(msg)
    else:
        log.info(f"Created stage: {name} ({prefix})")
        registry.register(stage)
        return stage


def load_stage_coros(config=None):
    """Provide co-routines for loading the stages defined in the
    configuration files.

    """
    if config is None:
        config = load_config()
    coros = set()
    for name, stage_data in config.get("stage", {}).items():
        coros.add(
            make_stage_device(
                name=name,
                prefix=stage_data["prefix"],
                pv_vert=stage_data["pv_vert"],
                pv_horiz=stage_data["pv_horiz"],
            )
        )
    return coros
