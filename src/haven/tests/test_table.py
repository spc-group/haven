from haven.instrument import Table, load_tables


def test_vertical_table():
    """A table that can only move up and down."""
    tbl = Table("255idcVME:", vertical_motor="m3", name="my_table")
    # Check that the correct components were created
    assert hasattr(tbl, "vertical")
    assert tbl.vertical.prefix == "255idcVME:m3"
    assert not hasattr(tbl, "horizontal")
    assert not hasattr(tbl, "upstream")
    assert not hasattr(tbl, "downstream")
    assert not hasattr(tbl, "pitch")
    assert not hasattr(tbl, "vertical_drive_transform")
    assert not hasattr(tbl, "vertical_readback_transform")


def test_horizontal_table():
    """A table that can only move left and right."""
    tbl = Table("255idcVME:", horizontal_motor="m3", name="my_table")
    # Check that the correct components were created
    assert not hasattr(tbl, "vertical")
    assert hasattr(tbl, "horizontal")
    assert tbl.horizontal.prefix == "255idcVME:m3"
    assert not hasattr(tbl, "upstream")
    assert not hasattr(tbl, "downstream")
    assert not hasattr(tbl, "pitch")
    assert not hasattr(tbl, "vertical_drive_transform")
    assert not hasattr(tbl, "vertical_readback_transform")


def test_pitch_table():
    """A table that can move vertical and adjust the angle."""
    tbl = Table(
        "255idcVME:",
        pseudo_motors="table_us:",
        transforms="table_us_trans:",
        upstream_motor="m3",
        downstream_motor="m4",
        name="my_table",
    )
    # Check that the correct components were created (or not)
    assert not hasattr(tbl, "horizontal")
    assert hasattr(tbl, "upstream")
    assert tbl.upstream.prefix == "255idcVME:m3"
    assert hasattr(tbl, "downstream")
    assert tbl.downstream.prefix == "255idcVME:m4"
    assert hasattr(tbl, "vertical")
    assert tbl.vertical.prefix == "255idcVME:table_us:height"
    assert hasattr(tbl, "pitch")
    assert tbl.pitch.prefix == "255idcVME:table_us:pitch"
    # Check the transforms
    assert hasattr(tbl, "vertical_drive_transform")
    assert tbl.vertical_drive_transform.prefix == "255idcVME:table_us_trans:Drive"
    assert hasattr(tbl, "vertical_readback_transform")
    assert tbl.vertical_readback_transform.prefix == "255idcVME:table_us_trans:Readback"


def test_load_tables(sim_registry):
    load_tables()
    # Check that the vertical/horizontal table has the right motors
    table = sim_registry.find(name="upstream_table")
    assert isinstance(table, Table)
    assert not hasattr(table, "upstream")
    assert not hasattr(table, "downstream")
    assert table.vertical.prefix == "255idcVME:m26"
    assert table.horizontal.prefix == "255idcVME:m25"
    # Check that the 2-leg table has the right motors
    table = sim_registry.find(name="downstream_table")
    assert isinstance(table, Table)
    assert table.upstream.prefix == "255idcVME:m21"
    assert table.downstream.prefix == "255idcVME:m22"
    assert table.vertical.prefix == "255idcVME:table_ds:height"
    assert not hasattr(table, "horizontal")
