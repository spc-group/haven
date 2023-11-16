import asyncio
import logging
import warnings

from apsbss.apsbss_ophyd import EpicsBssDevice
from apstools.devices.aps_machine import ApsMachineParametersDevice

from haven import registry

from .._iconfig import load_config
from .device import aload_devices, make_device

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


def load_aps_coros(config=None):
    """Load devices related to the synchrotron as a whole."""
    if config is None:
        config = load_config()
    # Load storage ring device
    yield make_device(ApsMachine, name="APS", labels={"synchrotrons"})
    yield make_device(EpicsBssDevice, name="bss", prefix=f"{config['bss']['prefix']}:")


def load_aps(config=None):
    asyncio.run(aload_devices(*load_aps_coros(config=config)))
