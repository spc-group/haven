from pathlib import Path
import pytest

from haven.simulated_ioc import simulated_ioc


ioc_dir = Path(__file__).parent.resolve() / "iocs"


@pytest.fixture(scope="session")
def ioc_undulator():
    with simulated_ioc(fp=ioc_dir / "undulator.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_mono():
    with simulated_ioc(fp=ioc_dir / "mono.py") as pvdb:
        yield pvdb


@pytest.fixture(scope="session")
def ioc_scaler():
    with simulated_ioc(fp=ioc_dir / "scaler.py") as pvdb:
        yield pvdb


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
