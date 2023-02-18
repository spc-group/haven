import pytest
from firefly.application import FireflyApplication


@pytest.fixture(scope="session")
def qapp_cls():
    return FireflyApplication
