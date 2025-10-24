import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--beamline",
        action="store_true",
        default=False,
        help="run tests that require a real beamline",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line(
        "markers", "beamline(devices): mark test that requires the beamline"
    )


def modify_beamline(config, items):
    if config.getoption("--beamline"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_beamline = pytest.mark.skip(reason="need --beamline option to run")
    for item in items:
        if "beamline" in item.keywords:
            item.add_marker(skip_beamline)


def modify_runslow(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


def pytest_collection_modifyitems(config, items):
    modify_runslow(config, items)
    modify_beamline(config, items)
