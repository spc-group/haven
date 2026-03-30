from haven.devices import Table


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
