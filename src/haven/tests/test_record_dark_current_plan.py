from pprint import pprint

from haven.plans.record_dark_current import record_dark_current
from haven.instrument.shutter import ShutterState


def test_shutters_get_reset(shutters, I0):
    shutter = shutters[0]
    msgs = list(record_dark_current(ion_chambers=[I0], shutters=[shutter]))
    pprint(msgs)
    # Check the shutters get closed
    set_shutter_msg = msgs[1]
    assert set_shutter_msg.command == "set"
    assert set_shutter_msg.obj is shutter
    assert set_shutter_msg.args[0] == ShutterState.CLOSED
    # Check the shutters get re-opened
    set_shutter_msg = msgs[-2]
    assert set_shutter_msg.command == "set"
    assert set_shutter_msg.obj is shutter
    assert set_shutter_msg.args[0] == ShutterState.OPEN
