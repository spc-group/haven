import re

from haven.instrument.load_instrument import load_instrument
from haven import registry
from haven.run_engine import RunEngine

# Import plans
from haven import energy_scan, xafs_scan, align_slits, knife_scan
from bluesky.plans import scan, rel_scan, list_scan, rel_list_scan, count

# Import devices
load_instrument()
for cpt in registry.components:
    name = re.sub('\W|^(?=\d)','_', cpt.name)
    globals()[name] = cpt

RE = RunEngine()




# start-re-manager --verbose --startup-script /home/beams/S25STAFF/src/haven/haven/queueserver_startup.py --existing-plans-devices /home/beams/S25STAFF/bluesky_25idc/queueserver_existing_plans_and_devices.yaml --user-group-permissions /home/beams/S25STAFF/bluesky_25idc/queueserver_user_group_permissions.yaml --zmq-publish-console ON --keep-re --update-existing-plans-devices ENVIRONMENT_OPEN
