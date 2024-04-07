import databroker  # noqa: F401
import matplotlib.pyplot as plt  # noqa: F401
from bluesky import RunEngine  # noqa: F401
from bluesky import suspenders  # noqa: F401
from bluesky import plan_stubs as bps  # noqa: F401
from bluesky import plans as bp  # noqa: F401
from bluesky.callbacks.best_effort import BestEffortCallback  # noqa: F401
from bluesky.simulators import summarize_plan  # noqa: F401

import haven  # noqa: F401

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
