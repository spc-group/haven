import asyncio
import uuid
from unittest.mock import MagicMock

import pytest
from ophyd_async.core import soft_signal_rw
from pydm.data_plugins import plugin_for_address
from pydm.widgets import PyDMChannel, PyDMLineEdit
from qtpy.QtCore import QObject
from qtpy.QtCore import Signal as QSignal

from firefly.pydm_plugin import HavenPlugin


@pytest.fixture()
async def plugin():
    _plugin = plugin_for_address("haven://")
    # For some reason, this lock doesn't get released when exiting tests
    _plugin.lock = MagicMock()
    return _plugin


def test_plugin_registered(plugin):
    assert isinstance(plugin, HavenPlugin)


async def test_signal_connection(qapp, qtbot, sim_registry, plugin):
    # Create a signal and attach our listener
    sig = soft_signal_rw(float, name="my_signal", initial_value=1)
    sim_registry.register(sig)
    widget = PyDMLineEdit(init_channel="haven://my_signal")
    qtbot.addWidget(widget)
    # Let the Qt event loop catch up
    await asyncio.sleep(0.1)
    qapp.processEvents()
    # Check that our widget receives the initial value
    assert widget._write_access
    assert widget._connected
    assert widget.value == 1


@pytest.fixture()
async def async_signal(sim_registry):
    # Get a unique name so we don't recycle channels
    signal_name = str(uuid.uuid4())
    # Create the signal
    sig = soft_signal_rw(float, initial_value=1.0, name=signal_name)
    await sig.connect(mock=False)
    sim_registry.use_typhos = False  # Typhos doesn't work with async anyway?
    sim_registry.register(sig)
    return sig


@pytest.fixture()
async def async_channel(qapp, qtbot, async_signal):

    class SigHolder(QObject):
        send_value = QSignal(float)

    sigs = SigHolder()
    channel = PyDMChannel(
        address=f"haven://{async_signal.name}",
        value_signal=sigs.send_value,
        write_access_slot=MagicMock(),
        connection_slot=MagicMock(),
        value_slot=MagicMock(),
    )
    channel.connect()
    # Wait for metadata task to complete
    try:
        task = [
            t
            for t in asyncio.all_tasks()
            if t.get_name() == f"meta_{async_signal.name}"
        ][0]
    except IndexError:
        # Connection already established
        pass
    else:
        await task
    # Execute the test code
    try:
        yield channel
    finally:
        channel.disconnect()


@pytest.mark.asyncio
async def test_async_signal_connection(async_channel, async_signal):
    # Check that our widget receives the initial values from the signal
    channel = async_channel
    assert channel.write_access_slot.called
    assert channel.connection_slot.called
    channel.value_slot.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_async_send_value(qtbot, qapp, async_channel, async_signal):
    """Can we update the ophyd signal from the channel?"""
    channel = async_channel
    signal = async_signal
    # Check our starting state
    assert (await signal.get_value()) == 1.0
    # Update the widget
    channel.value_signal.emit(2.0)
    for task in asyncio.all_tasks():
        try:
            await task
        except RuntimeError:
            pass
    # Check the updated value
    assert (await signal.get_value()) == 2.0


@pytest.mark.asyncio
async def test_async_gets_value(qtbot, qapp, async_channel, async_signal):
    """Can we update the channel from the ophyd signal?"""
    channel = async_channel
    signal = async_signal
    channel.value_slot.reset_mock()
    # Update the ophyd signal
    await signal.set(3.0)
    qapp.processEvents()
    # Check that the channel slot was updated
    channel.value_slot.assert_called_once_with(3.0)
