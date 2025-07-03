import math
from collections.abc import Iterator

from bluesky import Msg
from bluesky import plan_stubs as bps
from bluesky.preprocessors import plan_mutator

from haven.protocols import FixedOffsetMonochromator, Monochromator


def beam_offset(bragg: float, gap: float):
    """Calculate the offset in the beam height applied by a channel cut
    mono.

    Parameters
    ==========
    bragg
      The desired Bragg angle, in arcseconds.
    gap
      The spacing between the first and second crystal.

    Returns
    =======
    offset
      The change in position of the beam caused by the
      monochromator.

    """
    bragg = math.radians(bragg / 3600)
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

    def insert_primary_move(msg):
        def head(msg):
            old_secondary_offset = yield from bps.rd(secondary_mono.beam_offset)
            old_primary_offset = yield from bps.rd(primary_mono.beam_offset)
            bragg_offset = yield from bps.rd(secondary_mono.bragg_offset)
            gap = yield from bps.rd(secondary_mono.gap)
            # Calculate the new primary offset
            new_bragg = msg.args[0]
            new_secondary_offset = beam_offset(new_bragg + bragg_offset, gap=gap)
            new_primary_offset = (
                old_primary_offset + old_secondary_offset - new_secondary_offset
            )
            yield Msg(
                "set",
                primary_mono.beam_offset,
                new_primary_offset,
                run=msg.run,
                **msg.kwargs,
            )
            yield msg

        if msg.command == "set" and msg.obj is secondary_mono.bragg:
            return (head(msg), None)
        # Not a message we care about, just let it pass
        return (None, None)
    return (yield from plan_mutator(plan, insert_primary_move))
