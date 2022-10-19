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
        log.debug(f"Looking for motor number {motor_num}")
        prefix = f"{ioc}:m{motor_num}"
        # Take the name of the ophyd motor from the epics description
        name = epics.caget(f"{prefix}.DESC", timeout=1)
        if name is None:
            # The PV doesn't exist, so we've probably reached the highest motor number
            break
        # Create the motor device
        motor = HavenMotor(
            prefix=f"{ioc}:m{motor_num}",
            name=name,
            labels={"motors"},
        )
        log.info(f"Created motor {motor}")
        motors.append(motor)


vme_motors = prepare_motors(ioc=conf["motors"]["ioc"])
