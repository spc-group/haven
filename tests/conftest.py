import os
from pathlib import Path
import pytest
from qtpy import QtWidgets

from haven.simulated_ioc import simulated_ioc
from haven import registry
from firefly.application import FireflyApplication


ioc_dir = Path(__file__).parent.resolve() / "iocs"


# def pytest_collection_modifyitems(config, items):
#     """Skip tests if no X server is available.

#     Mark tests with ``@pytest.mark.needs_xserver`` to indicate tests
#     that should be skipped if no X-server is present.

#     """
#     # Check if we have X server available
#     has_x = os.environ.get('GITHUB_ACTIONS', 'false') != 'true'
#     if has_x:
#         return
#     # Skip items marked as needing an X-server
#     skip_nox = pytest.mark.skip(reason="No X-server available.")
#     for item in items:
#         if "needs_xserver" in item.keywords:
#             item.add_marker(skip_nox)


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
def ioc_scaler():
    with simulated_ioc(fp=ioc_dir / "scaler.py") as pvdb:
        yield pvdb


@pytest.fixture()
def ffapp():
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


@pytest.fixture
def sim_registry():
    # Clean the registry so we can restore it later
    components = registry.components
    registry.clear()
    # Run the test
    yield registry
    # Restore the previous registry components
    registry.components = components
