from ophyd import Device, FormattedComponent as FCpt, EpicsMotor
from ophyd import Component as Cpt, Signal

from .instrument_registry import registry
from .._iconfig import load_config


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


def load_stages(config=None):
    if config is None:
        config = load_config()
    for name, stage_data in config.get("stage", {}).items():
        XYStage(
            name=name,
            prefix=stage_data["prefix"],
            pv_vert=stage_data["pv_vert"],
            pv_horiz=stage_data["pv_horiz"],
        )


class AerotechFlyer(Device):
    """An Aerotech stage that allows for Flyscanning.

    Records a start and end position, step size and slew speed.
    """

    start_position = Cpt(Signal, name="start_position")
    end_position = Cpt(Signal, name="end_position")
    step_size = Cpt(Signal, name="step_size")
    slew_speed = Cpt(Signal, name="slew_speed")


class AerotechFlyStage(XYStage):
    """A subclass of XY stage for the Aerotech to include a flyer."""

    flyer = Cpt(AerotechFlyer, name="flyer", labels={"flyers"})
