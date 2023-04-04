import logging

import epics
from ophyd import EpicsMotor, EpicsSignal, Component as Cpt

from .._iconfig import load_config
from .instrument_registry import registry


log = logging.getLogger(__name__)


@registry.register
class HavenMotor(EpicsMotor):
    """The default motor for haven movement.

    Returns to the previous value when being unstaged.
    """
    description = Cpt(EpicsSignal, name="description", suffix=".DESC")
    tweak_value = Cpt(EpicsSignal, name="tweak_value", suffix=".TWV")
    tweak_forward = Cpt(EpicsSignal, name="tweak_forward", suffix=".TWF")
    tweak_reverse = Cpt(EpicsSignal, name="tweak_reverse", suffix=".TWR")
    soft_limit_violation = Cpt(EpicsSignal, name="soft_limit_violation", suffix=".LVIO")

    def stage(self):
        super().stage()
        # Save starting position to restore later
        self._old_value = self.user_readback.value

    def unstage(self):
        super().unstage()
        # Restore the previously saved position after the scan ends
        self.set(self._old_value, wait=True)


def load_all_motors(config=None):
    if config is None:
        config = load_config()
    # Figure out the prefix
    for name, config in config["motor"].items():
        prefix = config["prefix"]
        num_motors = config["num_motors"]
        log.info(f"Loading {num_motors} motors from IOC: {name} ({prefix})")
        load_ioc_motors(prefix=prefix, num_motors=num_motors, ioc_name=name)


def load_ioc_motors(prefix, num_motors, ioc_name=None):
    # Create motor objects
    motors = []
    for motor_num in range(num_motors):
        pv = f"{prefix}:m{motor_num+1}"
        # Take the name of the ophyd motor from the epics description
        log.debug(f"Looking for motor {motor_num} at {pv}")
        name = epics.caget(f"{pv}.DESC", timeout=1, use_monitor=False)
        if name is None:
            # The PV doesn't exist, so we've probably reached the highest motor number
            break
        # Create the motor device
        if name == f"motor {motor_num+1}":
            # It's an unnamed motor, so skip it
            log.debug(f"SKipping unnamed motor {motor_num}")
        else:
            # Create a new motor object
            labels = {"motors", "baseline"}
            if ioc_name is not None:
                labels = set([ioc_name, *labels])
            motor = HavenMotor(
                prefix=pv,
                name=name,
                labels=labels,
            )
            log.info(f"Created motor {motor}")
            motors.append(motor)
