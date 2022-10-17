import logging

import epics
from ophyd import EpicsMotor

from .._iconfig import load_config
from .instrument_registry import registry


log = logging.getLogger(__name__)
conf = load_config()


@registry.register
class HavenMotor(EpicsMotor):
    pass


def prepare_motors(ioc):
    # Figure out the prefix
    # Create motor objects
    motor_num = 0
    motors = []
    while True:
        motor_num += 1
        pv = f"{ioc}:m{motor_num}"
        # Take the name of the ophyd motor from the epics description
        log.debug(f"Looking for motor {motor_num} at {pv}")
        name = epics.caget(f"{pv}.DESC", timeout=1)
        if name is None:
            # The PV doesn't exist, so we've probably reached the highest motor number
            break
        # Create the motor device
        if name == f"motor {motor_num}":
            # It's an unnamed motor, so skip it
            log.debug(f"SKipping unnamed motor {motor_num}")
        else:
            # Create a new motor object
            motor = HavenMotor(
                prefix=pv,
                name=name,
                labels={"motors"},
            )
            log.debug(f"Created motor {motor}")
            motors.append(motor)

vme_motors = prepare_motors(ioc=conf["motors"]["ioc"])
