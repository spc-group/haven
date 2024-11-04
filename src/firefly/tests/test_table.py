import pytest

from firefly.table import TableDisplay
from haven.devices import Table


@pytest.fixture()
async def table(sim_registry):
    """A fake set of slits using the 4-blade setup."""
    tbl = Table(
        name="table",
        upstream_prefix="255idc:m1",
        downstream_prefix="255idc:m2",
        horizontal_prefix="255idc:m3",
        vertical_prefix="255idc:m2",
        pseudo_motor_prefix="255idc:table_ds:",
        transform_prefix="255idc:table_ds_trans:",
        labels={"tables"},
    )
    await tbl.connect(mock=True)
    return tbl


@pytest.fixture()
def empty_table(sim_registry):
    """A fake set of slits using the 4-blade setup."""
    tbl = Table(
        name="table",
    )
    sim_registry.register(tbl)
    return tbl


@pytest.fixture()
def display(qtbot, table):
    disp = TableDisplay(macros={"DEVICE": table.name})
    qtbot.addWidget(disp)
    return disp


def test_unused_motor_widgets(qtbot, empty_table):
    """Do control widgets get disable for motors that aren't on the device?"""
    display = TableDisplay(macros={"DEVICE": empty_table.name})
    qtbot.addWidget(display)
    # Check that the bender control widgets were enabled
    assert not display.ui.pitch_embedded_display.isEnabled()
    assert not display.ui.vertical_embedded_display.isEnabled()
    assert not display.ui.horizontal_embedded_display.isEnabled()
