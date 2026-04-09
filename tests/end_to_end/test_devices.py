import pytest
from bluesky import plan_stubs as bps
from guarneri.exceptions import ComponentNotFound
from ophyd_async.core import TriggerInfo

from haven import load_config


@pytest.mark.beamline()
def test_motor(startup):
    RE = startup.RE
    sim_motor_2 = startup.devices["sim_motor_2"]
    RE(startup.mv(sim_motor_2, 5))
    result = RE(bps.rd(sim_motor_2))
    RE(startup.mv(sim_motor_2, -5))
    result = RE(bps.rd(sim_motor_2))


cfg = load_config()
detector_tables = [
    "camera",
    "eiger",
    "ion_chamber",
    "lambda",
    "sim_detector",
    "xspress3",
]
tables = [getattr(cfg, table, []) for table in detector_tables]
detector_names = [section["name"] for table in tables for section in table]


@pytest.mark.beamline()
@pytest.mark.dependency()
@pytest.mark.parametrize("detector_name", detector_names)
async def test_trigger_detector(startup, detector_name):
    try:
        detector = startup.devices[detector_name]
    except ComponentNotFound:
        pytest.skip(reason=f"Detector '{detector_name}' not available")
    await detector.stage()
    try:
        await detector.prepare(TriggerInfo(livetime=0.1))
        await detector.trigger()
    finally:
        await detector.unstage()


# Pollutes tiled database, so only run it if the detectors are working
@pytest.mark.dependency(depends=["test_trigger_detectors"])
@pytest.mark.beamline()
@pytest.mark.asyncio
async def test_count_detectors(startup):
    # Use the detectors in an actual plan
    num_counts = 3
    detectors = startup.devices.findall(label="detectors", allow_none=True)
    if len(detectors) == 0:
        pytest.skip(reason="No detectors available")
    # Temporary: remove when test is stable
    # detectors = startup.devices.findall(name="sim_detector", allow_none=False)
    # Count the detector
    result = startup.RE(
        startup.count(detectors, num=num_counts), reason="end-to-end testing"
    )
    # Check that the results are in Tiled
    run = startup.writer.client[result.run_start_uids[0]]
    xarr = run["primary"].read()
    for detector in detectors:
        desc = await detector.describe()
        for signal in desc.keys():
            assert signal in xarr
            assert xarr[signal].shape[0] == num_counts


@pytest.mark.beamline()
def test_asymmetric_analyzer_energy_readback(startup):
    RE = startup.RE
    try:
        analyzer = startup.devices["herfd_analyzer"]
    except ComponentNotFound:
        pytest.skip("Device 'herfd_analyzer' not found.")
    mv = startup.mv
    RE(
        mv(
            analyzer.surface_plane,
            (9, 1, 1),
            analyzer.reflection,
            (6, 2, 0),
            analyzer.lattice_constant,
            5.43095,
            analyzer.crystal_yaw,
            108.23,
            analyzer.crystal_pitch,
            90.434,
            analyzer.chord,
            503785.54114,
        )
    )
    # Now read the
    result = RE(startup.rd(analyzer.energy))
    assert result.plan_result == pytest.approx(7415.6, abs=2)
