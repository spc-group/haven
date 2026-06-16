"""Customized versions of the standard bluesky plans."""

from collections.abc import Sequence
from itertools import chain, repeat
from typing import Any

import bluesky.plan_stubs as bps
import bluesky.plans as bp
from bluesky.protocols import Movable, Readable
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
        detectors,
        trigger_infos=trigger_infos,
        per_event=msg_per_step,
    )
    yield from bp.count(
        detectors=detectors,
        num=num,
        delay=delay,
        per_shot=per_shot,
        md=_md,
    )


def scan(
    detectors: Sequence[Readable],
    *args: Movable | Any,
    num: int | None = None,
    livetime: float = 0.0,
    collections_per_event: int = 1,
    per_step: bp.PerStep | None = None,
    md: CustomPlanMetadata = {},
) -> MsgGenerator[str]:
    """
    Scan over one multi-motor trajectory.

    Parameters
    ----------
    detectors : list or tuple
        list of 'readable' objects
    *args :
        For one dimension, ``motor, start, stop``.
        In general:

        .. code-block:: python

            motor1, start1, stop1,
            motor2, start2, stop2,
            ...,
            motorN, startN, stopN

        Motors can be any 'settable' object (motor, temp controller, etc.)
    num : integer
        number of points
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
    per_step : callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md : dict, optional
        metadata

    See Also
    --------
    :func:`bluesky.plans.relative_inner_product_scan`
    :func:`bluesky.plans.grid_scan`
    :func:`bluesky.plans.scan_nd`
    """
    md_args = list(
        chain(
            *(
                (repr(motor), start, stop)
                for motor, start, stop in bp.partition(3, args)
            )
        )
    )
    _md = {
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "num": num,
            "args": md_args,
            "livetime": livetime,
            "collections_per_event": collections_per_event,
            "per_step": repr(per_step),
        },
    }
    _md.update(md)
    # Add hook to prepare detectors for every trigger
    trigger_infos = repeat(
        TriggerInfo(livetime=livetime, collections_per_event=collections_per_event)
    )
    msg_per_step: bp.PerStep = per_step if per_step else bps.one_nd_step
    msg_per_step = prepare_per_event(
        detectors,
        trigger_infos=trigger_infos,
        per_event=msg_per_step,
    )
    yield from bp.scan(detectors, *args, num=num, per_step=msg_per_step, md=_md)


def rel_scan(
    detectors: Sequence[Readable],
    *args: Movable | Any,
    num=None,
    livetime: float = 0.0,
    collections_per_event: int = 1,
    per_step: bp.PerStep | None = None,
    md: CustomPlanMetadata = {},
) -> MsgGenerator[str]:
    """
    Scan over one multi-motor trajectory relative to current position.

    Parameters
    ----------
    detectors : list
        list of 'readable' objects
    *args :
        For one dimension, ``motor, start, stop``.
        In general:

        .. code-block:: python

            motor1, start1, stop1,
            motor2, start2, start2,
            ...,
            motorN, startN, stopN,

        Motors can be any 'settable' object (motor, temp controller, etc.)
    num : integer
        number of points
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
    per_step : callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md : dict, optional
        metadata

    See Also
    --------
    :func:`bluesky.plans.rel_grid_scan`
    :func:`bluesky.plans.inner_product_scan`
    :func:`bluesky.plans.scan_nd`
    """
    md_args = list(
        chain(
            *(
                (repr(motor), start, stop)
                for motor, start, stop in bp.partition(3, args)
            )
        )
    )
    _md = {
        "plan_args": {
            "detectors": list(map(repr, detectors)),
            "num": num,
            "args": md_args,
            "livetime": livetime,
            "collections_per_event": collections_per_event,
            "per_step": repr(per_step),
        },
    }
    _md.update(md)
    # Add hook to prepare detectors for every trigger
    trigger_infos = repeat(
        TriggerInfo(livetime=livetime, collections_per_event=collections_per_event)
    )
    msg_per_step: bp.PerStep = per_step if per_step else bps.one_nd_step
    msg_per_step = prepare_per_event(
        detectors,
        trigger_infos=trigger_infos,
        per_event=msg_per_step,
    )
    yield from bp.rel_scan(detectors, *args, num=num, per_step=msg_per_step, md=_md)
