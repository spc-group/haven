from apstools.devices.aps_machine import ApsMachineParametersDevice
from haven import registry


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
    aps_ = ApsMachine(name="APS", labels={"synchrotrons"})
    registry.register(aps_)
