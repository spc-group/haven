from bluesky.plans import scan
from ophyd_async.core import Device

from haven import auto_shutter_wrapper


def test_auto_shutter_wrapper():
    # Prepare fake devices
    detector = Device()
    motor = Device()
    # Build the wrapped plan
    plan = scan([detector], motor, 0, 10, num=1)
    plan = auto_shutter_wrapper(plan)
