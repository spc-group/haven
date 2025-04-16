import logging
import re  # noqa: F401

import databroker  # noqa: F401
from bluesky.plan_stubs import abs_set  # noqa: F401
from bluesky.plan_stubs import mv as _mv, mvr as _mvr  # noqa: F401
from bluesky.plan_stubs import null, pause, rel_set, sleep, stop  # noqa: F401
from bluesky.run_engine import call_in_bluesky_event_loop
from ophyd_async.core import NotConnected

# Import plans
from haven import beamline, recall_motor_position, sanitize_name  # noqa: F401
from haven.plans import (  # noqa: F401
    auto_gain,
    count,
    energy_scan,
    grid_scan as _grid_scan,
    list_scan,
    record_dark_current,
    rel_grid_scan as _rel_grid_scan,
    rel_list_scan,
    rel_scan,
    scan,
    scan_nd,
    set_energy,
    xafs_scan,
)
from haven.run_engine import run_engine  # noqa: F401

log = logging.getLogger(__name__)

# Create a run engine
RE = run_engine(
    connect_databroker=False, connect_tiled=False, connect_kafka=True, use_bec=False
)

# Import devices
beamline.load()
try:
    call_in_bluesky_event_loop(beamline.connect())
except NotConnected as exc:
    log.exception(exc)
for cpt in beamline.devices.all_devices:
    # Make sure we're not adding a readback value with the same name
    # as its parent.
    if cpt.parent is not None and cpt.name == cpt.parent.name:
        continue
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


def mvr(
    *args, group=None, **kwargs
):
    """
    Move one or more devices to a relative setpoint. Wait for all to complete.

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
    :func:`bluesky.plan_stubs.rel_set`
    :func:`bluesky.plan_stubs.mv`
    """
    yield from _mvr(*args, group=group, **kwargs)


    
def grid_scan(
    detectors,
    *args,
    snake_axes = None,
    per_step = None,
    md = None,
):
    """
    Scan over a mesh; each motor is on an independent trajectory.

    Parameters
    ----------
    detectors: list or tuple
        list of 'readable' objects
    ``*args``
        patterned like (``motor1, start1, stop1, num1,``
                        ``motor2, start2, stop2, num2,``
                        ``motor3, start3, stop3, num3,`` ...
                        ``motorN, startN, stopN, numN``)

        The first motor is the "slowest", the outer loop. For all motors
        except the first motor, there is a "snake" argument: a boolean
        indicating whether to following snake-like, winding trajectory or a
        simple left-to-right trajectory.
    snake_axes: boolean or iterable, optional
        which axes should be snaked, either ``False`` (do not snake any axes),
        ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
        is defined as following snake-like, winding trajectory instead of a
        simple left-to-right trajectory. The elements of the list are motors
        that are listed in `args`. The list must not contain the slowest
        (first) motor, since it can't be snaked.
    per_step: callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md: dict, optional
        metadata

    See Also
    --------
    :func:`bluesky.plans.rel_grid_scan`
    :func:`bluesky.plans.inner_product_scan`
    :func:`bluesky.plans.scan_nd`
    """
    yield from _grid_scan(
        detectors,
        *args,
        snake_axes=snake_axes,
        per_step=per_step,
        md=md
    )


def rel_grid_scan(
    detectors,
    *args,
    snake_axes = None,
    per_step = None,
    md = None,
):
    """
    Scan over a mesh relative to current position.

    Parameters
    ----------
    detectors: list
        list of 'readable' objects
    ``*args``
        patterned like (``motor1, start1, stop1, num1,``
                        ``motor2, start2, stop2, num2,``
                        ``motor3, start3, stop3, num3,`` ...
                        ``motorN, startN, stopN, numN``)

        The first motor is the "slowest", the outer loop. For all motors
        except the first motor, there is a "snake" argument: a boolean
        indicating whether to following snake-like, winding trajectory or a
        simple left-to-right trajectory.
    snake_axes: boolean or iterable, optional
        which axes should be snaked, either ``False`` (do not snake any axes),
        ``True`` (snake all axes) or a list of axes to snake. "Snaking" an axis
        is defined as following snake-like, winding trajectory instead of a
        simple left-to-right trajectory. The elements of the list are motors
        that are listed in `args`. The list must not contain the slowest
        (first) motor, since it can't be snaked.
    per_step: callable, optional
        hook for customizing action of inner loop (messages per step).
        See docstring of :func:`bluesky.plan_stubs.one_nd_step` (the default)
        for details.
    md: dict, optional
        metadata

    See Also
    --------
    :func:`bluesky.plans.relative_inner_product_scan`
    :func:`bluesky.plans.grid_scan`
    :func:`bluesky.plans.scan_nd`
    """
    yield from _rel_grid_scan(
        detectors,
        *args,
        snake_axes=snake_axes,
        per_step=per_step,
        md=md
    )
