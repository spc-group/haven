# get_ipython().run_line_magic("matplotlib",  "qt")

from bluesky import plans as bp, plan_stubs as bps, RunEngine, suspenders
from bluesky.simulators import summarize_plan
import databroker

# Set up live-plotting
# from bluesky.utils import install_qt_kicker
# install_qt_kicker()

import haven
config = haven.load_config()
print(f"Initializing {config['beamline']['name']}...", end="", flush=True)
haven.load_instrument()
print("done")
RE = RunEngine()

# Give the RunEngine time to initialize it's async magic?? (MFW)
import time
time.sleep(1.)

# Add metadata and data-saving to the run engine
catalog = databroker.catalog['bluesky']
def save_data(name, doc):
    catalog.v1.insert(name, doc)
RE.subscribe(save_data)
RE.preprocessors.append(haven.preprocessors.inject_haven_md_wrapper)

# Install suspenders
aps = haven.registry.find("APS")

# Suspend when shutter permit is disabled
RE.install_suspender(
    suspenders.SuspendWhenChanged(
        signal=aps.shutter_permit,
        expected_value="PERMIT",
        allow_resume=True,
        sleep=3,
        tripped_message="Shutter permit revoked.",
    )
)

# Monitor shutter open/close status for A and C stations
for shutter in haven.registry.findall("shutters"):
    RE.install_suspender(suspenders.SuspendBoolLow(shutter.pss_state, sleep=3))
