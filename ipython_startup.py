from bluesky import plans as bp, plan_stubs as bps, RunEngine, suspenders
from bluesky.simulators import summarize_plan
from bluesky.callbacks.best_effort import BestEffortCallback
import databroker

# Set up live-plotting
# from bluesky.utils import install_qt_kicker
# install_qt_kicker()

import haven
config = haven.load_config()
print(f"Initializing {config['beamline']['name']}...", end="", flush=True)
haven.load_instrument()
print("done")
RE = haven.run_engine()

# Set up best effort callback for visualizing live data
bec = BestEffortCallback()
RE.subscribe(bec)

# Add metadata to the run engine
RE.preprocessors.append(haven.preprocessors.inject_haven_md_wrapper)
