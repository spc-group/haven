import subprocess
from subprocess import Popen, PIPE
import shutil
import time
from pathlib import Path
import os

from qtpy import QtWidgets
from tiled.client import from_uri
from tiled.client.cache import Cache
import pytest
from unittest import mock
from ophyd.sim import (
    instantiate_fake_device,
    make_fake_device,
    fake_device_cache,
    FakeEpicsSignal,
)
from pydm.data_plugins import add_plugin

import haven
from haven.simulated_ioc import simulated_ioc
from haven import load_config, registry
from haven._iconfig import beamline_connected as _beamline_connected
from haven.instrument.stage import AerotechFlyer, AerotechStage
from haven.instrument.aps import ApsMachine
from haven.instrument.shutter import Shutter
from haven.instrument.camera import AravisDetector
from haven.instrument.delay import EpicsSignalWithIO
from haven.instrument.dxp import DxpDetectorBase, add_mcas as add_dxp_mcas
from haven.instrument.ion_chamber import IonChamber
from haven.instrument.xspress import Xspress3Detector, add_mcas as add_xspress_mcas
from firefly.application import FireflyApplication
from firefly.ophyd_plugin import OphydPlugin

# from run_engine import RunEngineStub
from firefly.application import FireflyApplication


top_dir = Path(__file__).parent.resolve()
ioc_dir = top_dir / "tests" / "iocs"
haven_dir = top_dir / "src" / "haven"
test_dir = top_dir / "tests"


# Specify the configuration files to use for testing
os.environ["HAVEN_CONFIG_FILES"] = ",".join(
    [
        f"{test_dir/'iconfig_testing.toml'}",
        f"{haven_dir/'iconfig_default.toml'}",
    ]
)


class FakeEpicsSignalWithIO(FakeEpicsSignal):
    # An EPICS signal that simply uses the DG-645 convention of
    # 'AO' being the setpoint and 'AI' being the read-back
    _metadata_keys = EpicsSignalWithIO._metadata_keys

    def __init__(self, prefix, **kwargs):
        super().__init__(f"{prefix}I", write_pv=f"{prefix}O", **kwargs)


fake_device_cache[EpicsSignalWithIO] = FakeEpicsSignalWithIO


@pytest.fixture()
def beamline_connected():
    with _beamline_connected(True):
        yield


@pytest.fixture(scope="session")
def qapp_cls():
    return FireflyApplication


def pytest_configure(config):
    app = QtWidgets.QApplication.instance()
    assert app is None
    app = FireflyApplication()
    app = QtWidgets.QApplication.instance()
    assert isinstance(app, FireflyApplication)
    # # Create event loop for asyncio stuff
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)


def tiled_is_running(port, match_command=True):
    lsof = subprocess.run(["lsof", "-i", f":{port}", "-F"], capture_output=True)
    assert lsof.stderr.decode() == ""
    stdout = lsof.stdout.decode().split("\n")
    is_running = len(stdout) >= 3
    if match_command:
        is_running = is_running and stdout[3] == "ctiled"
    return is_running


@pytest.fixture(scope="session")
def sim_tiled():
    """Start a tiled server using production data from 25-ID."""
    timeout = 20
    port = "8337"

    if tiled_is_running(port, match_command=False):
        raise RuntimeError(f"Port {port} is already in use.")
    tiled_bin = shutil.which("tiled")
    process = Popen(
        [
            tiled_bin,
            "serve",
            "pyobject",
            "--public",
            "--port",
            str(port),
            "haven.tests.tiled_example:tree",
        ]
    )
    # Wait for start to complete
    for i in range(timeout):
        if tiled_is_running(port):
            break
        time.sleep(1.0)
    else:
        # Timeout finished without startup or error
        process.kill()
        raise TimeoutError
    # Prepare the client
    client = from_uri(f"http://localhost:{port}", cache=Cache())
    try:
        yield client
    finally:
        # Shut down
        process.terminate()
        # Wait for start to complete
        for i in range(timeout):
            if not tiled_is_running(port):
                break
            time.sleep(1.0)
        else:
            process.kill()
            time.sleep(1)


@pytest.fixture()
def sim_registry(monkeypatch):
    # mock out Ophyd connections so devices can be created
    modules = [
        haven.instrument.fluorescence_detector,
        haven.instrument.monochromator,
        haven.instrument.ion_chamber,
        haven.instrument.motor,
        haven.instrument.device,
    ]
    for mod in modules:
        monkeypatch.setattr(mod, "await_for_connection", mock.AsyncMock())
    monkeypatch.setattr(
        haven.instrument.ion_chamber, "caget", mock.AsyncMock(return_value="I0")
    )
    # Clean the registry so we can restore it later
    registry = haven.registry
    objects_by_name = registry._objects_by_name
    objects_by_label = registry._objects_by_label
    registry.clear()
    # Run the test
    yield registry
    # Restore the previous registry components
    registry._objects_by_name = objects_by_name
    registry._objects_by_label = objects_by_label


@pytest.fixture()
def sim_ion_chamber(sim_registry):
    FakeIonChamber = make_fake_device(IonChamber)
    ion_chamber = FakeIonChamber(
        prefix="scaler_ioc", name="I00", labels={"ion_chambers"}, ch_num=2
    )
    sim_registry.register(ion_chamber)
    return ion_chamber


@pytest.fixture()
def I0(sim_registry):
    """A fake ion chamber named 'I0' on scaler channel 2."""
    FakeIonChamber = make_fake_device(IonChamber)
    ion_chamber = FakeIonChamber(
        prefix="scaler_ioc", name="I0", labels={"ion_chambers"}, ch_num=2
    )
    sim_registry.register(ion_chamber)
    return ion_chamber


@pytest.fixture()
def It(sim_registry):
    """A fake ion chamber named 'It' on scaler channel 3."""
    FakeIonChamber = make_fake_device(IonChamber)
    ion_chamber = FakeIonChamber(
        prefix="scaler_ioc", name="It", labels={"ion_chambers"}, ch_num=3
    )
    sim_registry.register(ion_chamber)
    return ion_chamber


@pytest.fixture(scope="session")
def pydm_ophyd_plugin():
    return add_plugin(OphydPlugin)


@pytest.fixture()
def ffapp(pydm_ophyd_plugin):
    # Get an instance of the application
    app = FireflyApplication.instance()
    assert isinstance(app, FireflyApplication)
    if app is None:
        app = FireflyApplication()
    # Set up the actions and other boildplate stuff
    app.setup_window_actions()
    app.setup_runengine_actions()
    assert isinstance(app, FireflyApplication)
    yield app
    if hasattr(app, "_queue_thread"):
        app._queue_thread.quit()
