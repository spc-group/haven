from bluesky import plan_stubs as bps

from haven.protocols import FixedOffsetMonochromator, Monochromator


def align_monochromators(
    primary_mono: FixedOffsetMonochromator,
    secondary_mono: Monochromator,
    primary_offset: float,
):
    """A plan to align a series of two monochromators with one-another.

    Parameters
    ==========
    primary_mono
      The first monochromator in the series.
    secondary_mono
      The second monochromator in the series.

    """
    yield from bps.mv(
        primary_mono.beam_offset,
        primary_offset,
        secondary_mono.vertical,
        primary_offset,
    )
