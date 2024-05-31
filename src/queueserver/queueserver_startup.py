import re

from haven.instrument.load_instrument import load_instrument, load_simulated_devices
from haven import registry
from haven.run_engine import run_engine
import databroker

# Import plans
from haven import energy_scan, xafs_scan, align_slits, knife_scan, set_energy, auto_gain, calibrate_mono_gap, align_pitch2, recall_motor_position
from bluesky.plans import count, scan, rel_scan, list_scan, rel_list_scan, grid_scan, rel_grid_scan, scan_nd
from bluesky.plan_stubs import abs_set, rel_set, mv, mvr, sleep, pause, stop, null

# Import devices
load_instrument()
load_simulated_devices()
print(registry.device_names)
for cpt in registry._objects_by_name.values():
    # Replace spaces and other illegal characters in variable name
    # name = re.sub('\W|^(?=\d)','_', cpt.name)
    # Add the device as a variable in module's globals
    globals()[cpt.name] = cpt

# Create a run engine without all the bells and whistles
RE = run_engine(connect_databroker=False, use_bec=False)
