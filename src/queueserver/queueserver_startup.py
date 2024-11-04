import logging
import re  # noqa: F401

import bluesky.preprocessors as bpp  # noqa: F401
import databroker  # noqa: F401
from bluesky.plan_stubs import (  # noqa: F401
    abs_set,
    mv,
    mvr,
    null,
    pause,
    rel_set,
    sleep,
    stop,
)
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
try:
    call_in_bluesky_event_loop(beamline.load())
except NotConnected as exc:
    log.exception(exc)
for cpt in beamline.registry._objects_by_name.values():
    # Replace spaces and other illegal characters in variable name
    # name = re.sub('\W|^(?=\d)','_', cpt.name)
    name = sanitize_name(cpt.name)
    # Add the device as a variable in module's globals
    globals().setdefault(name, cpt)
