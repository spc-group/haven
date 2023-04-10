from ophyd import EpicsSignal, EpicsMotor
from pydm.data_plugins import plugin_for_address, add_plugin
from pydm import PyDMChannel

from firefly.ophyd_plugin import OphydConnection, OphydPlugin


def test_ophyd_pydm_ophyd_plugin(pydm_ophyd_plugin):
    plugin = plugin_for_address("oph://sim_detector")
    assert isinstance(plugin, OphydPlugin)


def test_signal_pv_lookup(sim_registry, pydm_ophyd_plugin):
    """Check that the device name gets converted to a PV for a simple ophyd.EpicsSignal."""
    # Create a ophyd signal
    signal = EpicsSignal("the_pv", name="epics_signal")
    sim_registry.register(signal)
    # Have the pydm_ophyd_plugin handle a channel
    channel = PyDMChannel(address="oph://epics_signal")
    pydm_ophyd_plugin.add_connection(channel)
    # Check that the connection was correctly retrieved from the
    # device registry
    connection = pydm_ophyd_plugin.connections["epics_signal"]
    assert connection.pv.pvname == "the_pv"


def test_device_pv_lookup(sim_registry, pydm_ophyd_plugin):
    """Check that the device name gets converted to a PV for a simple ophyd.EpicsSignal."""
    # Create an ophyd device
    signal = EpicsMotor("the_record", name="epics_motor")
    sim_registry.register(signal)
    # Have the pydm_ophyd_plugin handle a channel
    channel = PyDMChannel(address="oph://epics_motor_user_setpoint")
    pydm_ophyd_plugin.add_connection(channel)
    # Check that the connection was correctly retrieved from the
    # device registry
    connection = pydm_ophyd_plugin.connections["epics_motor_user_setpoint"]
    assert connection.pv.pvname == "the_record.VAL"


def test_bad_pv_lookup(sim_registry, pydm_ophyd_plugin):
    """Check that invalid or missing ophyd names are handled gracefully."""
    # Create a ophyd device
    signal = EpicsMotor("the_record", name="epics_motor")
    sim_registry.register(signal)
    # Look for a component that isn't a leaf (i.e. not an EpicsSignal)
    channel = PyDMChannel(address="oph://epics_motor")
    pydm_ophyd_plugin.add_connection(channel)
    # Check that the original address is set for widget feedback
    connection = pydm_ophyd_plugin.connections["epics_motor"]
    assert connection.pv.pvname == "epics_motor"
    # Look for a component that isn't in the registry
    channel = PyDMChannel(address="oph://jabberwocky")
    pydm_ophyd_plugin.add_connection(channel)
    # Check that the original address is set for widget feedback
    connection = pydm_ophyd_plugin.connections["jabberwocky"]
    assert connection.pv.pvname == "jabberwocky"
