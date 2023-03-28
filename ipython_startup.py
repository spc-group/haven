from bluesky import plans as bp, plan_stubs as bps, RunEngine, suspenders
from bluesky.simulators import summarize_plan
from bluesky.callbacks.best_effort import BestEffortCallback
import databroker
import matplotlib.pyplot as plt

import haven

# Prepare the haven instrument
config = haven.load_config()
print(f"Initializing {config['beamline']['name']}...", end="", flush=True)
haven.load_instrument()
print("done")
RE = haven.run_engine()
ion_chambers = haven.registry.findall("ion_chambers")

# Set up best effort callback for visualizing live data
plt.ion()
bec = BestEffortCallback()
RE.subscribe(bec)

# Add metadata to the run engine
RE.preprocessors.append(haven.preprocessors.inject_haven_md_wrapper)
