from collections.abc import Sequence
from uuid import uuid4

from bluesky import plan_stubs as bps
from bluesky import plans as bp
from bluesky.preprocessors import plan_mutator
from bluesky.protocols import Preparable, Readable
from bluesky.utils import CustomPlanMetadata, Msg, MsgGenerator, ScalarOrIterableFloat
from ophyd_async.core import TriggerInfo


def prepare_detectors_wrapper(
    plan, detectors: Sequence[Preparable], trigger_info: TriggerInfo
):
    """Insert messages to prepare any detectors before the first time they
    are triggered.

    """
    state = {"have_prepared": False}

    def head(msg: Msg) -> MsgGenerator:
        group = str(uuid4())
        yield from bps.broadcast_msg("prepare", detectors, trigger_info, group=group)
        yield from bps.wait(group=group)
        state["have_prepared"] = True
        yield msg

    def insert_prepare(msg: Msg):
        if state["have_prepared"] or msg.command != "trigger":
            # Not a message we care about, so just let it pass
            return (None, None)
        return (head(msg), None)

    return (yield from plan_mutator(plan, insert_prepare))


def count_multiple(
    detectors: Sequence[Readable],
    num: int | None = 1,
    delay: ScalarOrIterableFloat = 0.0,
    *,
    collections_per_event: int = 1,
    per_shot: bp.PerShot | None = None,
    md: CustomPlanMetadata | None = None,
) -> MsgGenerator[str]:
    """Take one or more readings from detectors, possibly many frames
    at once.

    Parameters
    ----------
    detectors
      List of 'readable' objects
    num : integer, optional
      Number of readings to take; default is 1. If None, capture data
      until canceled
    delay
      Time delay in seconds between successive readings; default is 0.
    collections_per_event
      How many frames to measure per count event.
    per_shot
      Hook for customizing action of inner loop (messages per step)
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
    # Build metadata
    _md = {
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "num": num,
            "delay": delay,
            "collections_per_event": collections_per_event,
        },
        "plan_name": "count_multiple",
    }
    _md.update(md or {})
    # Start with the standard bp.count plan as a base
    plan = bp.count(detectors, num=num, delay=delay, per_shot=per_shot, md=_md)
    # Wrap it so it prepares the detectors for multiple frames
    if collections_per_event > 1:
        trigger_info = TriggerInfo(collections_per_event=collections_per_event)
        plan = prepare_detectors_wrapper(
            plan, detectors=detectors, trigger_info=trigger_info
        )
    yield from plan
