import pytest

from haven.instrument import Table, load_tables


def test_vertical_table():
    """A table that can only move up and down."""
    tbl = Table(vertical_prefix="255idcVME:m3", name="my_table")
    # Check that the correct components were created
    assert hasattr(tbl, "vertical")
    assert tbl.vertical.user_setpoint.source == "ca://255idcVME:m3.VAL"
    assert not hasattr(tbl, "horizontal")
    assert not hasattr(tbl, "upstream")
    assert not hasattr(tbl, "downstream")
    assert not hasattr(tbl, "pitch")
    assert not hasattr(tbl, "vertical_drive_transform")
    assert not hasattr(tbl, "vertical_readback_transform")


def test_horizontal_table():
    """A table that can only move left and right."""
    tbl = Table(horizontal_prefix="255idVME:m3", name="my_table")
    # Check that the correct components were created
    assert not hasattr(tbl, "vertical")
    assert hasattr(tbl, "horizontal")
    assert tbl.horizontal.user_setpoint.source == "ca://255idVME:m3.VAL"
    assert not hasattr(tbl, "upstream")
    assert not hasattr(tbl, "downstream")
    assert not hasattr(tbl, "pitch")
    assert not hasattr(tbl, "vertical_drive_transform")
    assert not hasattr(tbl, "vertical_readback_transform")


def test_pitch_table():
    """A table that can move vertical and adjust the angle."""
    tbl = Table(
        pseudo_motor_prefix="255idcVME:table_us:",
        transform_prefix="255idcVME:table_us_trans:",
        upstream_prefix="255idcVME:m3",
        downstream_prefix="255idcVME:m4",
        name="my_table",
    )
    # Check that the correct components were created (or not)
    assert not hasattr(tbl, "horizontal")
    assert hasattr(tbl, "upstream")
    assert tbl.upstream.user_readback.source == "ca://255idcVME:m3.RBV"
    assert hasattr(tbl, "downstream")
    assert tbl.downstream.user_readback.source == "ca://255idcVME:m4.RBV"
    assert hasattr(tbl, "vertical")
    assert tbl.vertical.user_readback.source == "ca://255idcVME:table_us:height.RBV"
    assert hasattr(tbl, "pitch")
    assert tbl.pitch.user_readback.source == "ca://255idcVME:table_us:pitch.RBV"
    # Check the transforms
    assert hasattr(tbl, "vertical_drive_transform")
    assert (
        tbl.vertical_drive_transform.units.source
        == "ca://255idcVME:table_us_trans:Drive.EGU"
    )
    assert hasattr(tbl, "vertical_readback_transform")
    assert (
        tbl.vertical_readback_transform.units.source
        == "ca://255idcVME:table_us_trans:Readback.EGU"
    )


@pytest.mark.asyncio
async def test_load_tables(sim_registry):
    await load_tables(registry=sim_registry)
    # Check that the vertical/horizontal table has the right motors
    table = sim_registry.find(name="upstream_table")
    assert isinstance(table, Table)
    assert not hasattr(table, "upstream")
    assert not hasattr(table, "downstream")
    assert table.vertical.user_setpoint.source == "mock+ca://255idcVME:m26.VAL"
    assert table.horizontal.user_setpoint.source == "mock+ca://255idcVME:m25.VAL"
    # Check that the 2-leg table has the right motors
    table = sim_registry.find(name="downstream_table")
    assert isinstance(table, Table)
    assert table.upstream.user_setpoint.source == "mock+ca://255idcVME:m21.VAL"
    assert table.downstream.user_setpoint.source == "mock+ca://255idcVME:m22.VAL"
    assert (
        table.vertical.user_setpoint.source == "mock+ca://255idcVME:table_ds:height.VAL"
    )
    assert not hasattr(table, "horizontal")
