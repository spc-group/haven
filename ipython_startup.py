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
RE = haven.run_engine()

# Add metadata and data-saving to the run engine
catalog = databroker.catalog['bluesky']
def save_data(name, doc):
    catalog.v1.insert(name, doc)
RE.subscribe(save_data)
RE.preprocessors.append(haven.preprocessors.inject_haven_md_wrapper)
