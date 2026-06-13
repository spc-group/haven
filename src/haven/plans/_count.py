from collections.abc import Sequence
from itertools import repeat

import bluesky.plan_stubs as bps
from bluesky import plans as bp
from bluesky.protocols import Readable
from bluesky.utils import CustomPlanMetadata, MsgGenerator, ScalarOrIterableFloat
from ophyd_async.core import TriggerInfo

from ._prepare import prepare_per_event


def count(
    detectors: Sequence[Readable],
    num: int | None = 1,
    delay: ScalarOrIterableFloat = 0.0,
    *,
    livetime: float = 0.0,
    collections_per_event: int = 1,
    per_shot: bp.PerShot | None = None,
    md: CustomPlanMetadata = {},
) -> MsgGenerator[str]:
    """Take one or more readings from detectors.

    Parameters
    ----------
    detectors : list or tuple
        list of 'readable' objects
    num : integer, optional
        number of readings to take; default is 1

        If None, capture data until canceled
    delay : iterable or scalar, optional
        Time delay in seconds between successive readings; default is 0.
    livetime
        How long should each exposure be. 0 means whatever is
        currently set.
    collections_per_event
        A collection is exposed to bluesky as data, but different
        detectors can be set to have a different number of collections
        per event so that multiple collections from a faster detector
        can be zipped with a single collection from a slower
        detector. E.g. if number_of_events=10 and
        collections_per_event=5 then the detector will take 50
        exposures, but publish 10 StreamDatum indices, and describe()
        will show a shape of (5, h, w) for each.
    per_shot : callable, optional
        hook for customizing action of inner loop (messages per step)
        Expected signature ::

           def f(detectors: Iterable[OphydObj]) -> Generator[Msg]:
               ...

    md : dict, optional
        metadata

    Notes
    -----
    If ``delay`` is an iterable, it must have at least ``num - 1`` entries or
    the plan will raise a ``ValueError`` during iteration.

    """
    _md = {
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "num": num,
            "delay": delay,
            "livetime": livetime,
            "collections_per_event": collections_per_event,
        },
    }
    _md.update(md)
    # Add hook to prepare detectors for every trigger
    trigger_infos = repeat(
        TriggerInfo(livetime=livetime, collections_per_event=collections_per_event)
    )
    msg_per_step: bp.PerShot = per_shot if per_shot else bps.one_shot
    per_shot = prepare_per_event(
        detectors, trigger_infos=trigger_infos, per_event=msg_per_step
    )

    yield from bp.count(
        detectors=detectors,
        num=num,
        delay=delay,
        per_shot=per_shot,
        md=_md,
    )
