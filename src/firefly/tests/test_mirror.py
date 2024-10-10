import pytest

from firefly.mirror import MirrorDisplay
from haven.devices.mirrors import HighHeatLoadMirror


@pytest.fixture()
async def hhl_bendable_mirror(sim_registry):
    """A fake set of slits using the 4-blade setup."""
    mirr = HighHeatLoadMirror(prefix="255ida:ORM1:", name="hhl_mirror", bendable=True)
    await mirr.connect(mock=True)
    sim_registry.register(mirr)
    return mirr


async def test_bendable_mirror(hhl_bendable_mirror, qtbot):
    mirror = hhl_bendable_mirror
    display = MirrorDisplay(macros={"DEVICE": mirror.name})
    qtbot.addWidget(display)
    # Check that the bender controls are unlocked
    assert display.ui.bender_embedded_display.isEnabled()
