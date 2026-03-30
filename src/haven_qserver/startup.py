import logging
import re  # noqa: F401

from bluesky.plan_stubs import abs_set  # noqa: F401
from bluesky.plan_stubs import mv as mv  # noqa: F401
from bluesky.plan_stubs import mvr, null, pause, rel_set, sleep, stop  # noqa: F401
from bluesky.run_engine import call_in_bluesky_event_loop
from ophyd_async.core import NotConnected

# Import plans
from haven import beamline, recall_motor_position, sanitize_name  # noqa: F401
from haven.plans import (  # noqa: F401
    auto_gain,
    calibrate,
    count,
    energy_scan,
    grid_scan,
    list_scan,
    record_dark_current,
    rel_grid_scan,
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
RE = run_engine(connect_tiled=False, use_bec=False)

# Import devices
beamline.load()
try:
    call_in_bluesky_event_loop(beamline.connect())
except NotConnected as exc:
    log.exception(exc)
for device in beamline.devices.root_devices:
    # Add the device as a variable in module's globals
    globals().setdefault(device.name, device)
