import os
from pathlib import Path
import pytest
from qtpy import QtWidgets
import ophyd
from ophyd.sim import instantiate_fake_device, make_fake_device
from pydm.data_plugins import add_plugin


top_dir = Path(__file__).parent.parent.resolve()
ioc_dir = top_dir / "tests" / "iocs"
haven_dir = top_dir / "haven"
test_dir = top_dir / "tests"


from haven.simulated_ioc import simulated_ioc
from haven import registry, load_config
from haven.instrument.aps import ApsMachine
from haven.instrument.shutter import Shutter
from firefly.application import FireflyApplication
from firefly.ophyd_plugin import OphydPlugin


# Specify the configuration files to use for testing
os.environ["HAVEN_CONFIG_FILES"] = ",".join([
    f"{test_dir/'iconfig_testing.toml'}",
    f"{haven_dir/'iconfig_default.toml'}",
])
load_config.cache_clear()


def pytest_configure(config):
    app = QtWidgets.QApplication.instance()
    assert app is None
    app = FireflyApplication()
    app = QtWidgets.QApplication.instance()
    assert isinstance(app, FireflyApplication)


@pytest.fixture(scope="session")
def qapp_cls():
    return FireflyApplication


@pytest.fixture
def sim_registry():
    # Clean the registry so we can restore it later
    components = registry.components
    registry.clear()
    # Run the test
    yield registry
    # Restore the previous registry components
    registry.components = components


@pytest.fixture(scope="session")
def ioc_undulator():
    with simulated_ioc(fp=ioc_dir / "undulator.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_mono():
    with simulated_ioc(fp=ioc_dir / "mono.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_area_detector():
    with simulated_ioc(fp=ioc_dir / "area_detector.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_bss():
    with simulated_ioc(fp=ioc_dir / "apsbss_.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_scaler():
    with simulated_ioc(fp=ioc_dir / "scaler.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_ptc10():
    with simulated_ioc(fp=ioc_dir / "ptc10.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def pydm_ophyd_plugin():
    return add_plugin(OphydPlugin)


@pytest.fixture()
def ffapp(pydm_ophyd_plugin):
    # Get an instance of the application
    app = FireflyApplication.instance()
    if app is None:
        app = FireflyApplication()
    # Set up the actions and other boildplate stuff
    app.setup_window_actions()
    app.setup_runengine_actions()
    assert isinstance(app, FireflyApplication)
    yield app
    if hasattr(app, "_queue_thread"):
        app._queue_thread.quit()


@pytest.fixture(scope="session")
def ioc_motor():
    with simulated_ioc(fp=ioc_dir / "motor.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_preamp():
    with simulated_ioc(fp=ioc_dir / "preamp.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_simple():
    with simulated_ioc(fp=ioc_dir / "simple.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_vortex():
    with simulated_ioc(fp=ioc_dir / "vortex.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_mono():
    with simulated_ioc(fp=ioc_dir / "mono.py") as pvdb:
        yield pvdb


@pytest.fixture()
def sim_registry():
    # Clean the registry so we can restore it later
    components = registry.components
    registry.clear()
    # Run the test
    yield registry
    # Restore the previous registry components
    registry.components = components


# Simulated devices
@pytest.fixture()
def sim_aps(sim_registry):
    aps = instantiate_fake_device(ApsMachine, name="APS")
    sim_registry.register(aps)
    yield aps


@pytest.fixture()
def sim_shutters(sim_registry):
    FakeShutter = make_fake_device(Shutter)
    kw = dict(
        open_pv="_prefix", close_pv="_prefix2", state_pv="_prefix2", labels={"shutters"}
    )
    shutters = [
        FakeShutter(name="Shutter A", **kw),
        FakeShutter(name="Shutter C", **kw),
    ]
    # Registry with the simulated registry
    for shutter in shutters:
        sim_registry.register(shutter)
    yield shutters
