from pathlib import PurePath

import pytest
import pytest_asyncio
from bluesky.run_engine import RunEngine
from ophyd_async.core import StaticPathProvider, UUIDFilenameProvider

from haven import devices, load_config, plans


def pytest_generate_tests(metafunc):
    all_params = load_config().device_parameters().get("lambda", [])
    if "lambda_detector" in metafunc.fixturenames:
        metafunc.parametrize("lambda_detector", all_params, indirect=True)


@pytest_asyncio.fixture
async def lambda_detector(request):
    kwargs = {**request.param}
    path_provider = StaticPathProvider(
        filename_provider=UUIDFilenameProvider(),
        directory_path=PurePath("/tmp/"),
    )
    det = devices.LambdaDetector(**kwargs, path_provider=path_provider)
    await det.connect()
    old_acquire_time = await det.driver.acquire_time.get_value()
    await det.driver.acquire_time.set(0.01)
    try:
        yield det
    finally:
        await det.driver.acquire_time.set(old_acquire_time)


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
    RE = RunEngine({})
    docs = {}

    def stash_docs(name, doc):
        docs[name] = [*docs.get(name, []), doc]

    RE.subscribe(stash_docs)
    num_calls = 5
    for i in range(num_calls):
        RE(plans.count_multiple([lambda_detector], collections_per_event=10))
    # Make sure the right number of documents were emitted
    assert len(docs["start"]) == num_calls
    assert len(docs["descriptor"]) == num_calls
    assert len(docs["stream_resource"]) == num_calls
    assert len(docs["stream_datum"]) == num_calls
    assert len(docs["event"]) == num_calls
    assert len(docs["stop"]) == num_calls
