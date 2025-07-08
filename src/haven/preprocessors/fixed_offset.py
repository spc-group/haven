import math
from collections.abc import Iterator

from bluesky import Msg
from bluesky import plan_stubs as bps
from bluesky.preprocessors import plan_mutator
from pint import Quantity

from haven.protocols import FixedOffsetMonochromator, Monochromator
from haven.units import energy_to_bragg, ureg


def beam_offset(bragg: Quantity, gap: Quantity) -> Quantity:
    """Calculate the offset in the beam height applied by a channel cut
    mono.

    Parameters
    ==========
    bragg
      The desired Bragg angle.
    gap
      The spacing between the first and second crystal.

    Returns
    =======
    offset
      The change in position of the beam caused by the
      monochromator.

    """
    return 2 * gap * math.cos(bragg)


def fixed_offset_wrapper(
    plan: Iterator,
    primary_mono: FixedOffsetMonochromator,
    secondary_mono: Monochromator,
):
    """A preprocessor that keeps the beam at a constant offset between two
    monochromators.

    Parameters
    ----------
    plan
        a generator, list, or similar containing `Msg` objects
    primary_mono
      The mono that will adjust its offset to account for the offset
      caused by *secondary_mono*
    secondary_mono
      The mono that will cause a variable offset to the beam.

    Yields
    ------
    msg : Msg
        Messages from *plan*, with messages inserted to control the mono
        coupling.

    """
    # Read starting state so we can use it for calculations later
    secondary_offset = (yield from bps.rd(secondary_mono.beam_offset)) * ureg.microns
    primary_offset = (yield from bps.rd(primary_mono.beam_offset)) * ureg.microns
    total_offset = secondary_offset + primary_offset
    bragg_offset = (yield from bps.rd(secondary_mono.bragg_offset)) * ureg.arcseconds
    gap = (yield from bps.rd(secondary_mono.gap)) * ureg.microns
    d_spacing = (yield from bps.rd(secondary_mono.d_spacing)) * ureg.angstrom

    def insert_primary_move(msg):
        def head(msg, bragg: float | None = None, energy: float | None = None):
            # Calculate bragg angle from energy, if necessary
            if bragg is None:
                bragg = energy_to_bragg(energy, d=d_spacing)
            # Calculate the new primary offset
            new_secondary_offset = beam_offset(bragg + bragg_offset, gap=gap)
            new_primary_offset = total_offset - new_secondary_offset
            yield Msg(
                "set",
                primary_mono.beam_offset,
                new_primary_offset.to(ureg.microns).magnitude,
                run=msg.run,
                **msg.kwargs,
            )
            yield msg

        if msg.command == "set" and msg.obj is secondary_mono.bragg:
            # If setting bragg angle
            return (head(msg, bragg=msg.args[0] * ureg.arcseconds), None)
        if msg.command == "set" and msg.obj is secondary_mono.energy:
            # If setting energy
            return (head(msg, energy=msg.args[0] * ureg.electron_volt), None)
        # Not a message we care about, so just let it pass
        return (None, None)

    return (yield from plan_mutator(plan, insert_primary_move))
