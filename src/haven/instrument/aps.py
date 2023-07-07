import logging
import warnings

from apstools.devices.aps_machine import ApsMachineParametersDevice
from apsbss.apsbss_ophyd import EpicsBssDevice

from haven import registry
from .._iconfig import load_config


log = logging.getLogger(__name__)


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
    devices = []
    if config is None:
        config = load_config()
    # Load storage ring device
    try:
        aps_ = ApsMachine(name="APS", labels={"synchrotrons"})
    except Exception as exc:
        msg = f"Could not instantiate APS machine: {repr(exc)}"
        log.warning(msg)
        warnings.warn(msg)
    else:
        registry.register(aps_)
        devices.append(aps_)
    # Load scheduling system device
    bss_ = EpicsBssDevice(prefix=f"{config['bss']['prefix']}:", name="bss")
    registry.register(bss_)
    devices.append(bss_)
    return devices
