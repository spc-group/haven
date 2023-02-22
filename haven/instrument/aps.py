from apstools.devices.aps_machine import ApsMachineParametersDevice
from haven import registry

def load_aps(config=None):
    """Load devices related to the synchrotron as a whole."""
    aps_ = ApsMachineParametersDevice(name="APS", labels={"synchrotrons"})
    registry.register(aps_)
