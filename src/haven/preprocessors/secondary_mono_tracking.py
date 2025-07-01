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


def secondary_mono_tracking_wrapper(
    plan: Iterator,
    secondary_mono: Monochromator,
    primary_mono: FixedOffsetMonochromator,
):
    """A preprocessor that causes the primary mono to track the position of the secondary mono.

    Parameters
    ----------
    plan : iterable or iterator
        a generator, list, or similar containing `Msg` objects

    Yields
    ------
    msg : Msg
        messages from plan, with 'set' messages inserted

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
