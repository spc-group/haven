from haven.instrument import table


def test_vertical_table():
    """A table that can only move up and down."""
    tbl = table.Table("255idcVME:table_ds:", vertical_motor="m3", name="my_table")
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
    tbl = table.Table("255idcVME:table_ds:", horizontal_motor="m3", name="my_table")
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
    tbl = table.Table("255idcVME:table_us:", upstream_motor="m3", downstream_motor="m4", name="my_table")
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
    
