import pytest
import pytest_asyncio
from bluesky.run_engine import RunEngine

from haven import devices, load_config


def pytest_generate_tests(metafunc):
    all_params = load_config().device_parameters().get("lambda", [])
    if "lambda_detector" in metafunc.fixturenames:
        metafunc.parametrize("lambda_detector", all_params, indirect=True)


@pytest_asyncio.fixture
async def lambda_detector(request):
    kwargs = {**request.param}
    det = devices.LambdaDetector(**kwargs)
    await det.connect()
    return det


@pytest.mark.beamline()
def test_count_mutiple_events(lambda_detector):
    """Test an early bug where the count_mutiple() plan sometimes misses
    events.

    For the below plan, sometimes the data look fine in Tiled,
    sometimes the `lambda_250k` stream is missing entirely.

    ```python
    haven.plans.count_multiple([lamba_250k], collections_per_event=1)
    ```

    """
    cfg = load_config()
    print(cfg.device_parameters()["lambda"])
    assert False
    return
    RE = RunEngine({})
    # with init_devices():
    #     detector = LambdaDetector("25idLamba
    docs = []

    def stash_docs(name, doc):
        docs.append((name, doc))

    RE.subscribe(stash_docs)
