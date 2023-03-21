from bluesky import plan_stubs as bps
from typing import Literal, Union, Sequence

from ..instrument.instrument_registry import registry
from ..typing import Motor


def _set_shutters(
    shutters: Union[str, Sequence[Motor]], direction: Literal["open", "closed"]
):
    shutters = registry.findall(shutters)
    # Prepare the plan
    plan_args = [obj for shutter in shutters for obj in (shutter, direction)]
    plan = bps.mv(*plan_args)
    # Emit the messages
    yield from plan


def open_shutters(shutters: Union[str, Sequence[Motor]] = "shutters"):
    """A plan to open the shutters.

    By default, this plan is greedy and will open all shutters defined
    at the beamline. If only specific shutters should be opened, they
    can be passed either as Device objects or device names as the
    *shutters* argument.

    E.g.
      RE(open_shutters(["Shutter C"]))

    E.g.
      shutter = haven.instrument.shutter.Shutter(..., name="Shutter C")
      RE(open_shutters([shutter]))

    This plan will temporarily remove the default shutter-related
    suspenders from the haven run engine.

    """
    yield from _set_shutters(shutters, "open")


def close_shutters(shutters: Union[str, Sequence[Motor]] = "shutters"):
    """A plan to close some shutters.

    By default, this plan is lazy and requires any shutters to be
    passed explicitly. Shutters can be passed either as Device objects
    or device names as the *shutters* argument.

    E.g.
      RE(close_shutters(["Shutter C"]))

    E.g.
      shutter = haven.instrument.shutter.Shutter(..., name="Shutter C")
      RE(close_shutters([shutter]))

    This plan will temporarily remove the default shutter-related
    suspenders from the haven run engine.

    """
    yield from _set_shutters(shutters, "closed")
