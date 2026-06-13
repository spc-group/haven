import uuid
from collections.abc import Iterator, Sequence
from functools import wraps

import bluesky.plan_stubs as bps
from bluesky.protocols import Preparable
from bluesky.utils import MsgGenerator
from ophyd_async.core import TriggerInfo


def prepare_per_event(
    detectors: Sequence[Preparable], trigger_infos: Iterator[TriggerInfo], per_event
):
    """Closure for preparing detectors at each event (step/shot/etc).

    The detectors will only be re-prepared if the next trigger info is
    different from the previous trigger info.

    Parameters
    ==========
    detectors
      The detector objects to prepare.
    trigger_infos
      At each event, the next trigger info will be used to prepare the
      detectors.
    per_event
      The callable to use after the detectors are prepared.

    """

    # Avoid name clashes
    preparables = detectors
    # past_exposures = []
    past_trigger_infos = [None]

    @wraps(per_event)
    def _per_step(*args, **kwargs) -> MsgGenerator[None]:
        """
        Inner loop of an N-dimensional step scan

        This is the default function for ``per_step`` param`` in ND plans.

        Parameters
        ----------
        detectors : list or tuple
            devices to read
        step : dict
            mapping motors to positions in this step
        pos_cache : dict
            mapping motors to their last-set positions
        take_reading : plan, optional
            function to do the actual acquisition ::

               def take_reading(dets, name='primary'):
                    yield from ...

            Callable[List[OphydObj], Optional[str]] -> Generator[Msg], optional

            Defaults to `trigger_and_read`

        Yields
        ------
        msg : Msg
        """
        # Prepare detectors so that the exposure time is set correctly.
        # Doing it this way makes sure the timeout is correct when triggering.
        tinfo = next(trigger_infos)
        prep_group = uuid.uuid4()
        if tinfo != past_trigger_infos[-1]:
            # This data point changes how the detector gets trigger,
            # so we need to re-prepare
            for det in preparables:
                yield from bps.prepare(det, tinfo, group=prep_group, wait=False)
            yield from bps.wait(group=prep_group)
            past_trigger_infos.append(tinfo)
        yield from per_event(*args, **kwargs)

    return _per_step
