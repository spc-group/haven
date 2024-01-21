import os
import subprocess
from pathlib import Path
from unittest import mock

import psutil

# from pydm.data_plugins import plugin_modules, add_plugin
import pydm
import pytest
from bluesky import RunEngine
from ophyd import DynamicDeviceComponent as DDC
from ophyd import Kind
from ophyd.sim import (
    FakeEpicsSignal,
    fake_device_cache,
    instantiate_fake_device,
    make_fake_device,
)
from pytestqt.qt_compat import qt_api

import haven
from firefly.application import FireflyApplication
from firefly.main_window import FireflyMainWindow
from haven._iconfig import beamline_connected as _beamline_connected
from haven.instrument.aerotech import AerotechStage
from haven.instrument.aps import ApsMachine
from haven.instrument.camera import AravisDetector
from haven.instrument.delay import EpicsSignalWithIO
from haven.instrument.dxp import DxpDetector
from haven.instrument.dxp import add_mcas as add_dxp_mcas
from haven.instrument.ion_chamber import IonChamber
from haven.instrument.shutter import Shutter
from haven.instrument.slits import ApertureSlits, BladeSlits
from haven.instrument.xspress import Xspress3Detector
from haven.instrument.xspress import add_mcas as add_xspress_mcas

top_dir = Path(__file__).parent.resolve()
haven_dir = top_dir / "haven"


# Specify the configuration files to use for testing
os.environ["HAVEN_CONFIG_FILES"] = ",".join(
    [
        f"{haven_dir/'iconfig_testing.toml'}",
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


class RunEngineStub(RunEngine):
    def __repr__(self):
        return "<run_engine.RunEngineStub>"


@pytest.fixture()
def RE(event_loop):
    return RunEngineStub(call_returns_result=True)


@pytest.fixture(scope="session")
def qapp_cls():
    return FireflyApplication


# def pytest_configure(config):
#     app = QtWidgets.QApplication.instance()
#     assert app is None
#     app = FireflyApplication()
#     app = QtWidgets.QApplication.instance()
#     assert isinstance(app, FireflyApplication)
#     # # Create event loop for asyncio stuff
#     # loop = asyncio.new_event_loop()
#     # asyncio.set_event_loop(loop)


def tiled_is_running(port, match_command=True):
    lsof = subprocess.run(["lsof", "-i", f":{port}", "-F"], capture_output=True)
    assert lsof.stderr.decode() == ""
    stdout = lsof.stdout.decode().split("\n")
    is_running = len(stdout) >= 3
    if match_command:
        is_running = is_running and stdout[3] == "ctiled"
    return is_running


def kill_process(process_name):
    processes = []
    for proc in psutil.process_iter():
        # check whether the process name matches
        if proc.name() == process_name:
            proc.kill()
            processes.append(proc)
    # Wait for them all the terminate
    [proc.wait(timeout=5) for proc in processes]


@pytest.fixture()
def sim_registry(monkeypatch):
    # mock out Ophyd connections so devices can be created
    modules = [
        haven.instrument.ion_chamber,
        haven.instrument.device,
    ]
    for mod in modules:
        monkeypatch.setattr(mod, "await_for_connection", mock.AsyncMock())
    monkeypatch.setattr(
        haven.instrument.ion_chamber, "caget", mock.AsyncMock(return_value="I0")
    )
    # Save the registry so we can restore it later
    registry = haven.registry
    use_typhos = registry.use_typhos
    objects_by_name = registry._objects_by_name
    objects_by_label = registry._objects_by_label
    registry.clear()
    # Run the test
    try:
        yield registry
    finally:
        # Restore the previous registry components
        registry.clear(clear_typhos=True)
        registry._objects_by_name = objects_by_name
        registry._objects_by_label = objects_by_label
        registry.use_typhos = use_typhos


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
        prefix="scaler_ioc",
        preamp_prefix="preamp_ioc:SR04:",
        name="I0",
        labels={"ion_chambers"},
        ch_num=2,
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


@pytest.fixture()
def blade_slits(sim_registry):
    """A fake set of slits using the 4-blade setup."""
    FakeSlits = make_fake_device(BladeSlits)
    slits = FakeSlits(prefix="255idc:KB_slits", name="kb_slits", labels={"slits"})
    sim_registry.register(slits)
    return slits


@pytest.fixture()
def aperture_slits(sim_registry):
    """A fake slit assembling using the rotary aperture design."""
    FakeSlits = make_fake_device(ApertureSlits)
    slits = FakeSlits(
        prefix="255ida:slits:US:", name="whitebeam_slits", labels={"slits"}
    )
    sim_registry.register(slits)
    return slits


@pytest.fixture()
def sim_camera(sim_registry):
    FakeCamera = make_fake_device(AravisDetector)
    camera = FakeCamera(name="s255id-gige-A", labels={"cameras", "area_detectors"})
    camera.pva.pv_name._readback = "255idSimDet:Pva1:Image"
    # Registry with the simulated registry
    sim_registry.register(camera)
    yield camera


class DxpVortex(DxpDetector):
    mcas = DDC(
        add_dxp_mcas(range_=[0, 1, 2, 3]),
        kind=Kind.normal | Kind.hinted,
        default_read_attrs=[f"mca{i}" for i in [0, 1, 2, 3]],
        default_configuration_attrs=[f"mca{i}" for i in [0, 1, 2, 3]],
    )


@pytest.fixture()
def dxp(sim_registry):
    FakeDXP = make_fake_device(DxpVortex)
    vortex = FakeDXP(name="vortex_me4", labels={"xrf_detectors", "detectors"})
    sim_registry.register(vortex)
    # vortex.net_cdf.dimensions.set([1477326, 1, 1])
    yield vortex


class Xspress3Vortex(Xspress3Detector):
    mcas = DDC(
        add_xspress_mcas(range_=[0, 1, 2, 3]),
        kind=Kind.normal | Kind.hinted,
        default_read_attrs=[f"mca{i}" for i in [0, 1, 2, 3]],
        default_configuration_attrs=[f"mca{i}" for i in [0, 1, 2, 3]],
    )


@pytest.fixture()
def xspress(sim_registry):
    FakeXspress = make_fake_device(Xspress3Vortex)
    vortex = FakeXspress(name="vortex_me4", labels={"xrf_detectors"})
    sim_registry.register(vortex)
    yield vortex


@pytest.fixture()
def aerotech():
    Stage = make_fake_device(
        AerotechStage,
    )
    stage = Stage(
        "255id",
        delay_prefix="255id:DG645",
        pv_horiz=":m1",
        pv_vert=":m2",
        name="aerotech",
    )
    return stage


@pytest.fixture()
def aerotech_flyer(aerotech):
    flyer = aerotech.horiz
    flyer.user_setpoint._limits = (0, 1000)
    flyer.send_command = mock.MagicMock()
    yield flyer


@pytest.fixture()
def aps(sim_registry):
    aps = instantiate_fake_device(ApsMachine, name="APS")
    sim_registry.register(aps)
    yield aps


@pytest.fixture()
def shutters(sim_registry):
    FakeShutter = make_fake_device(Shutter)
    kw = dict(
        prefix="_prefix",
        open_pv="_prefix",
        close_pv="_prefix2",
        state_pv="_prefix2",
        labels={"shutters"},
    )
    shutters = [
        FakeShutter(name="Shutter A", **kw),
        FakeShutter(name="Shutter C", **kw),
    ]
    # Registry with the simulated registry
    for shutter in shutters:
        sim_registry.register(shutter)
    yield shutters


@pytest.fixture(scope="session")
def pydm_ophyd_plugin():
    return pydm.data_plugins.plugin_for_address("sig://")


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


@pytest.fixture(scope="session")
def ffapp(pydm_ophyd_plugin, qapp_cls, qapp_args, pytestconfig):
    # Get an instance of the application
    app = qt_api.QtWidgets.QApplication.instance()
    if app is None:
        # New Application
        global _ffapp_instance
        _ffapp_instance = qapp_cls(qapp_args)
        app = _ffapp_instance
        name = pytestconfig.getini("qt_qapp_name")
        app.setApplicationName(name)
    # Make sure there's at least one Window, otherwise things get weird
    if getattr(app, "_dummy_main_window", None) is None:
        # Set up the actions and other boildplate stuff
        app.setup_window_actions()
        app.setup_runengine_actions()
        app._dummy_main_window = FireflyMainWindow()
    # Sanity check to make sure a QApplication was not created by mistake
    assert isinstance(app, FireflyApplication)
    # Yield the finalized application object
    try:
        yield app
    finally:
        if hasattr(app, "_queue_thread"):
            app._queue_thread.quit()
            app._queue_thread.wait(msecs=5000)


# holds a global QApplication instance created in the qapp fixture; keeping
# this reference alive avoids it being garbage collected too early
_ffapp_instance = None


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
