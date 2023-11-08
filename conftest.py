import subprocess
from subprocess import Popen, PIPE
from unittest import mock
import shutil
import time
from pathlib import Path
import os

from qtpy import QtWidgets
from qtpy.QtWidgets import QAction
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
from haven.instrument.dxp import DxpDetector, add_mcas as add_dxp_mcas
from haven.instrument.ion_chamber import IonChamber
from haven.instrument.xspress import Xspress3Detector, add_mcas as add_xspress_mcas
from firefly.application import FireflyApplication
from firefly.main_window import FireflyMainWindow
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


# @pytest.fixture()
# def ffapp(pydm_ophyd_plugin):
#     # Get an instance of the application
#     app = FireflyApplication.instance()
#     assert isinstance(app, FireflyApplication)
#     if app is None:
#         app = FireflyApplication()
#     # Set up the actions and other boildplate stuff
#     app.setup_window_actions()
#     app.setup_runengine_actions()
#     assert isinstance(app, FireflyApplication)
#     yield app
#     if hasattr(app, "_queue_thread"):
#         app._queue_thread.quit()

qs_status = {
    "msg": "RE Manager v0.0.18",
    "items_in_queue": 0,
    "items_in_history": 0,
    "running_item_uid": None,
    "manager_state": "idle",
    "queue_stop_pending": False,
    "worker_environment_exists": False,
    "worker_environment_state": "closed",
    "worker_background_tasks": 0,
    "re_state": None,
    "pause_pending": False,
    "run_list_uid": "4f2d48cc-980d-4472-b62b-6686caeb3833",
    "plan_queue_uid": "2b99ccd8-f69b-4a44-82d0-947d32c5d0a2",
    "plan_history_uid": "9af8e898-0f00-4e7a-8d97-0964c8d43f47",
    "devices_existing_uid": "51d8b88d-7457-42c4-b67f-097b168be96d",
    "plans_existing_uid": "65f11f60-0049-46f5-9eb3-9f1589c4a6dd",
    "devices_allowed_uid": "a5ddff29-917c-462e-ba66-399777d2442a",
    "plans_allowed_uid": "d1e907cd-cb92-4d68-baab-fe195754827e",
    "plan_queue_mode": {"loop": False},
    "task_results_uid": "159e1820-32be-4e01-ab03-e3478d12d288",
    "lock_info_uid": "c7fe6f73-91fc-457d-8db0-dfcecb2f2aba",
    "lock": {"environment": False, "queue": False},
}



@pytest.fixture()
def ffapp(pydm_ophyd_plugin):
    # Get an instance of the application
    app = FireflyApplication.instance()
    if app is None:
        # New Application
        app = FireflyApplication()
    # Set up the actions and other boildplate stuff
    app.setup_window_actions()
    app.setup_runengine_actions()
    # Create a fake queue server client API
    queue_api = mock.MagicMock()
    queue_api.status.return_value = qs_status
    queue_api.queue_start.return_value = {"success": True,}
    queue_api.devices_allowed.return_value = {"success": True, "devices_allowed": {}}
    app.prepare_queue_client(api=queue_api, start_thread=False)
    assert isinstance(app.queue_autoplay_action, QAction)
    # Make sure there's at least one Window, otherwise things get weird
    app._dummy_main_window = FireflyMainWindow()
    # Sanity check to make sure a QApplication was not created by mistake
    assert isinstance(app, FireflyApplication)
    # Yield the finalized application object
    try:
        yield app
    finally:
        if hasattr(app, "_queue_thread"):
            app._queue_thread.quit()
