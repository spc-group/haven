from apstools.devices.aps_machine import ApsMachineParametersDevice
from apsbss.apsbss_ophyd import EpicsBssDevice
from haven import registry

from .._iconfig import load_config


class ApsMachine(ApsMachineParametersDevice):
    _default_read_attrs = [
        "current",
        "lifetime",
    ]
    _default_configuration_attrs = [
        "aps_cycle",
        "machine_status",
        "operating_mode",
        "shutter_permit",
        "fill_number",
        "orbit_correction",
        "global_feedback",
        "global_feedback_h",
        "global_feedback_v",
        "operator_messages",
    ]


def load_aps(config=None):
    """Load devices related to the synchrotron as a whole."""
    if config is None:
        config = load_config()
    # Load storage ring device
    aps_ = ApsMachine(name="APS", labels={"synchrotrons"})
    registry.register(aps_)
    # Load scheduling system device
    bss_ = EpicsBssDevice(prefix=f"{config['bss']['prefix']}:", name="bss")
    registry.register(bss_)
    return [aps_, bss_]
