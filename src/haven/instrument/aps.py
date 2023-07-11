import logging
import warnings

from apstools.devices.aps_machine import ApsMachineParametersDevice
from apsbss.apsbss_ophyd import EpicsBssDevice

from haven import registry
from .._iconfig import load_config
from .device import await_for_connection


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


async def make_aps_device():
    aps_ = ApsMachine(name="APS", labels={"synchrotrons"})
    try:
        await await_for_connection(aps_)
    except TimeoutError as exc:
        msg = f"Could not connect to APS machine."
        log.warning(msg)
    else:
        registry.register(aps_)
        return aps_


async def make_bss_device(prefix):
    # Load scheduling system device
    bss_ = EpicsBssDevice(prefix=prefix, name="bss")
    try:
        await await_for_connection(bss_)
    except TimeoutError as exc:
        msg = f"Could not connect to BSS system: {prefix}"
        log.warning(msg)
    else:
        registry.register(bss_)
        return bss_


def load_aps_coros(config=None):
    """Load devices related to the synchrotron as a whole."""
    coros = set()
    if config is None:
        config = load_config()
    # Load storage ring device
    coros.add(make_aps_device())
    coros.add(make_bss_device(prefix=f"{config['bss']['prefix']}:"))
    return coros
