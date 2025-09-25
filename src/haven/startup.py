"""Load plans/devices/etc. for interactive REPL sessions and the Haven
qserver."""

import logging
import time

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
from ophyd_async.core import NotConnected
from ophydregistry import ComponentNotFound

import haven  # noqa: F401

# Import plans (needed for the qserver, optional for ipython/firefly)
from haven import plans  # noqa: F401
from haven import recall_motor_position  # noqa: F401
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

logging.basicConfig(level=logging.WARNING)

log = logging.getLogger(__name__)


# Load the Tiled catalog for reading data back outline
catalog = haven.tiled_client()

# Create a run engine
RE = haven.run_engine(
    connect_tiled=True,
    call_returns_result=True,
)
try:
    autoawait_in_bluesky_event_loop()
except AssertionError:
    log.info("Autoawait not installed.")


# Prepare the haven instrument
config = haven.load_config()
t0 = time.monotonic()
rich.print(f"Initializing [bold cyan]{config['beamline']['name']}[/]…", flush=True)
loader_exception = None
haven.beamline.load()
try:
    call_in_bluesky_event_loop(haven.beamline.connect())
except NotConnected as exc:
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
del NotConnected
del ComponentNotFound
del rich
