import pytest
import pytest_asyncio
from ophyd_async.core import set_mock_value

from haven.devices import CL3000


@pytest_asyncio.fixture()
async def cl3k():
    cl = CL3000(name="rainbow", prefix="255idc:CL3K:1:")
    await cl.connect(mock=True)
    return cl


def test_signal_sources(cl3k):
    assert cl3k.measurement_type.source == "mock+ca://255idc:CL3K:1:measType"
    assert cl3k.measurement_rate.source == "mock+ca://255idc:CL3K:1:measurement.SCAN"
    assert cl3k.auto_zeroing.source == "mock+ca://255idc:CL3K:1:autoZero"
    assert cl3k.scaling.source == "mock+ca://255idc:CL3K:1:scaling_RBV"
    assert cl3k.offset.source == "mock+ca://255idc:CL3K:1:offset_RBV"
    assert cl3k.displacement.source == "mock+ca://255idc:CL3K:1:measurement_RBV"
    assert cl3k.counts.source == "mock+ca://255idc:CL3K:1:Count_RBV"
    assert cl3k.result.source == "mock+ca://255idc:CL3K:1:resultInfo_RBV"
    assert cl3k.judgement.source == "mock+ca://255idc:CL3K:1:judgement_RBV"


@pytest.mark.asyncio
async def test_readings(cl3k):
    set_mock_value(cl3k.displacement, 0.5)
    reading = await cl3k.read()
    assert set(reading.keys()) == {"rainbow-displacement"}
    assert reading["rainbow-displacement"]["value"] == 0.5
    config = await cl3k.read_configuration()
    assert set(config.keys()) == {
        "rainbow-measurement_type",
        "rainbow-measurement_rate",
        "rainbow-auto_zeroing",
        "rainbow-scaling",
        "rainbow-offset",
    }
