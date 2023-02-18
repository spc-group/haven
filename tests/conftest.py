from pathlib import Path
import pytest

from haven.simulated_ioc import simulated_ioc
from haven import registry


ioc_dir = Path(__file__).parent.parent.parent.resolve() / "haven" / "tests" / "iocs"


@pytest.fixture()
def ffapp(qapp):
    yield qapp
    if hasattr(qapp, "_queue_thread"):
        qapp._queue_thread.quit()


@pytest.fixture(scope="session")
def ioc_motor():
    with simulated_ioc(fp=ioc_dir / "motor.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_simple():
    with simulated_ioc(fp=ioc_dir / "simple.py") as pvdb:
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
