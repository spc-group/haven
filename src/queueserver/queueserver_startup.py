import logging
import re  # noqa: F401

import bluesky.preprocessors as bpp  # noqa: F401
import databroker  # noqa: F401
from bluesky.plan_stubs import abs_set  # noqa: F401
from bluesky.plan_stubs import mv as _mv  # noqa: F401
from bluesky.plan_stubs import mvr, null, pause, rel_set, sleep, stop  # noqa: F401
from bluesky.plans import (  # noqa: F401
    count,
    grid_scan,
    list_scan,
    rel_grid_scan,
    rel_list_scan,
    rel_scan,
    scan,
    scan_nd,
)
from bluesky.run_engine import call_in_bluesky_event_loop
from ophyd_async.core import NotConnected

# Import plans
from haven import beamline  # noqa: F401
from haven import (  # noqa: F401
    align_pitch2,
    align_slits,
    auto_gain,
    energy_scan,
    knife_scan,
    recall_motor_position,
    record_dark_current,
    sanitize_name,
    set_energy,
    xafs_scan,
)
from haven.run_engine import run_engine  # noqa: F401

log = logging.getLogger(__name__)

# Create a run engine without all the bells and whistles
RE = run_engine(connect_databroker=False, use_bec=False)

# Import devices
beamline.load()
try:
    call_in_bluesky_event_loop(beamline.connect())
except NotConnected as exc:
    log.exception(exc)
for cpt in beamline.devices._objects_by_name.values():
    # Replace spaces and other illegal characters in variable name
    # name = re.sub('\W|^(?=\d)','_', cpt.name)
    name = sanitize_name(cpt.name)
    # Add the device as a variable in module's globals
    globals().setdefault(name, cpt)


# Workaround for https://github.com/bluesky/bluesky-queueserver/issues/310
from collections.abc import Hashable


def mv(
    *args,
    group: Hashable | None = None,
    **kwargs,
):
    """
    Move one or more devices to a setpoint. Wait for all to complete.

    If more than one device is specified, the movements are done in parallel.

    Parameters
    ----------
    args :
        device1, value1, device2, value2, ...
    group : string, optional
        Used to mark these as a unit to be waited on.
    kwargs :
        passed to obj.set()

    Yields
    ------
    msg : Msg

    Returns
    -------
    statuses :
        Tuple of n statuses, one for each move operation

    See Also
    --------
    :func:`bluesky.plan_stubs.abs_set`
    :func:`bluesky.plan_stubs.mvr`
    """
    yield from _mv(*args, group=group, **kwargs)
