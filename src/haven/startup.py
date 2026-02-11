"""Load plans/devices/etc. for interactive REPL sessions and the Haven
qserver."""

import logging
import time
from collections.abc import Callable
from functools import partial

import numpy as np  # noqa: F401
import rich
from bluesky import plan_stubs as bps  # noqa: F401
from bluesky import plans as bp  # noqa: F401
from bluesky import preprocessors as bpp  # noqa: F401
from bluesky.plan_stubs import mv, mvr, rd  # noqa: F401
from bluesky.run_engine import (  # noqa: F401
    RunEngine,
    autoawait_in_bluesky_event_loop,
    call_in_bluesky_event_loop,
)
from bluesky.simulators import summarize_plan  # noqa: F401
from bluesky_queueserver import is_re_worker_active
from guarneri.exceptions import ComponentNotFound
from ophyd_async.core import NotConnectedError

import haven  # noqa: F401

# Import plans (needed for the qserver, optional for ipython/firefly)
from haven import plans  # noqa: F401
from haven.plans import (  # noqa: F401
    auto_gain,
    calibrate,
    count,
    emission_map_scan,
    energy_scan,
    fly_scan,
    grid_fly_scan,
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
from haven.preprocessors import fixed_offset_wrapper  # noqa: F401

logging.basicConfig(level=logging.WARNING)

log = logging.getLogger(__name__)

config = haven.load_config()


# Create a run engine
writer = haven.tiled_writer(config["tiled"]) if "tiled" in config else None
RE = haven.run_engine(
    tiled_writer=writer,
    call_returns_result=not is_re_worker_active(),
)
try:
    autoawait_in_bluesky_event_loop()
except AssertionError:
    log.info("Autoawait not installed.")


# Prepare the haven instrument
t0 = time.monotonic()
beamline_name = config.get("beamline", {}).get("name", "UNKNOWN BEAMLINE")
rich.print(f"Initializing [bold cyan]{beamline_name}[/]…", flush=True)
loader_exception = None
haven.beamline.load()
use_mocks = config.get("devices", {}).get("mock", False)
try:
    call_in_bluesky_event_loop(haven.beamline.connect(mock=use_mocks))
except NotConnectedError as exc:
    log.exception(exc)
    # Save the exception so we can alert the user later
    loader_exception = exc
num_devices = len(haven.beamline.devices.root_devices)
rich.print(
    f"Connected to {num_devices} devices in {time.monotonic() - t0:.2f} seconds.",
    flush=True,
)
del num_devices

# Save references to all the devices in the global namespace
devices = haven.beamline.devices
ion_chambers = devices.findall("ion_chambers", allow_none=True)
for cpt in devices.root_devices:
    # Make sure we're not adding a readback value with the same name
    # as its parent.
    if cpt.parent is not None and cpt.name == cpt.parent.name:
        continue
    # Replace spaces and other illegal characters in variable name
    name = haven.sanitize_name(cpt.name)
    # Add the device as a variable in module's globals
    globals().setdefault(name, cpt)

# Plan Decorators
# ===============
#
# Add plan decorators that require specific devices to be loaded
plan_decorators: list[Callable] = []

# Suspenders for if the storage ring goes down
try:
    aps = haven.beamline.devices["synchrotrons"]
except ComponentNotFound:
    log.info("APS device not found, suspenders not installed.")
else:
    # Suspend when shutter permit is disabled or storage ring current is too low
    shutters = haven.beamline.devices.findall("endstation_shutter", allow_none=True)
    plan_decorators.append(
        haven.preprocessors.aps_suspenders_decorator(aps=aps, shutters=shutters)
    )

plan_decorator = haven.plans.chain(*plan_decorators)

auto_gain = plan_decorator(auto_gain)
count = plan_decorator(count)
energy_scan = plan_decorator(energy_scan)
fly_scan = plan_decorator(fly_scan)
grid_scan = plan_decorator(grid_scan)
grid_fly_scan = plan_decorator(grid_fly_scan)
list_scan = plan_decorator(list_scan)
rel_grid_scan = plan_decorator(rel_grid_scan)
rel_list_scan = plan_decorator(rel_list_scan)
rel_scan = plan_decorator(rel_scan)
scan = plan_decorator(scan)
scan_nd = plan_decorator(scan_nd)
xafs_scan = plan_decorator(xafs_scan)


# Apply a wrapper for keeping the beam at a fixed offset
try:
    wrapper = partial(
        fixed_offset_wrapper,
        primary_mono=haven.beamline.devices["monochromator"],
        secondary_mono=haven.beamline.devices["secondary_mono"],
    )
except ComponentNotFound as exc:
    log.info(f"Could not couple mono offsets: {exc}")
else:
    RE.preprocessors.append(wrapper)

# Print helpful information to the console
custom_theme = rich.theme.Theme(
    {
        "code": "white on grey27",
    }
)
console = rich.console.Console(theme=custom_theme)
motd = (
    "[bold]Devices[/bold] are available directly by name or though the [italic]devices[/italic].\n"
    " ┣━ [code]m2 = sim_motor_2[/]\n"
    " ┃    —or—\n"
    " ┗━ [code]m2 = devices['sim_motor_2'][/]\n"
    "\n"
    "[bold]Haven plans and plan-stubs[/bold] are available as "
    "[italic]plans[/].\n"
    " ┗━ [code]plan = plans.xafs_scan(ion_chambers, -50, 100, 1, E0=8333)[/]\n"
    "\n"
    "The [bold]RunEngine[/bold] is available as [italic]RE[/italic].\n"
    " ┗━ [code]RE(bps.mv(m2, 2))[/code]\n"
    "\n"
    "The run engine is also registered as the transform [italic]<[/].\n"
    " ┣━ [code]<mv(m, 2)[/code] (absolute move)\n"
    " ┣━ [code]<mvr(m, 2)[/code] (relative move)\n"
    " ┗━ [code]<rd(m)[/code] (read)\n"
    "\n"
    "Run [code]help(haven)[/code] for more information."
)
rich.print("")  # Blank line for separation
console.print(
    rich.panel.Panel(
        motd,
        title="Welcome to the [bold purple]Haven[/] beamline control system.",
        subtitle="[link=https://haven-spc.readthedocs.io/en/latest/]haven-spc.readthedocs.io[/]",
        expand=False,
    )
)

# Make an alert in case devices did not connect properly
if loader_exception is not None:
    msg = "Some devices did not connect properly! See logs for details."
    console.print(
        rich.align.Align.center(f"\n[bold red][blink]:fire:[/]{msg}[blink]:fire:[/][/]")
    )

# Clean up the namespace by removing tokens that are only useful
# inside this script
del logging
del time
del RunEngine
del autoawait_in_bluesky_event_loop
del call_in_bluesky_event_loop
del NotConnectedError
del ComponentNotFound
del rich
