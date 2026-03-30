from haven.devices.mirrors import HighHeatLoadMirror, KBMirror, KBMirrors


async def test_high_heat_load_mirror_PVs():
    mirror = HighHeatLoadMirror(prefix="255ida:ORM2:", name="orm2", bendable=True)
    await mirror.connect(mock=True)
    # Check the motor PVs
    assert mirror.transverse.user_readback.source == "mock+ca://255ida:ORM2:m1.RBV"
    assert mirror.roll.user_setpoint.source == "mock+ca://255ida:ORM2:m2.VAL"
    assert mirror.upstream.user_setpoint.source == "mock+ca://255ida:ORM2:m3.VAL"
    assert mirror.downstream.user_setpoint.source == "mock+ca://255ida:ORM2:m4.VAL"
    assert mirror.normal.user_setpoint.source == "mock+ca://255ida:ORM2:lateral.VAL"
    assert mirror.pitch.user_setpoint.source == "mock+ca://255ida:ORM2:coarsePitch.VAL"
    assert mirror.bender.user_setpoint.source == "mock+ca://255ida:ORM2:m5.VAL"
    # Check the transform PVs
    assert (
        mirror.drive_transform.channel_B.input_pv.source
        == "mock+ca://255ida:ORM2:lats:Drive.INPB"
    )
    assert (
        mirror.readback_transform.channel_B.input_pv.source
        == "mock+ca://255ida:ORM2:lats:Readback.INPB"
    )


async def test_kb_mirrors_PVs():
    kb = KBMirrors(
        prefix="255idcVME:LongKB_Cdn:",
        horiz_upstream_motor="255idcVME:m33",
        horiz_downstream_motor="255idcVME:m34",
        vert_upstream_motor="255idcVME:m35",
        vert_downstream_motor="255idcVME:m36",
        name="kb",
    )
    await kb.connect(mock=True)
    # Check that the individual mirrors are there
    assert isinstance(kb.vert, KBMirror)
    assert isinstance(kb.horiz, KBMirror)
    # Check PVs
    assert (
        kb.horiz.pitch.user_setpoint.source
        == "mock+ca://255idcVME:LongKB_Cdn:H:pitch.VAL"
    )
    assert (
        kb.vert.normal.user_setpoint.source
        == "mock+ca://255idcVME:LongKB_Cdn:V:height.VAL"
    )
    assert kb.horiz.upstream.user_setpoint.source == "mock+ca://255idcVME:m33.VAL"
    assert kb.horiz.downstream.user_setpoint.source == "mock+ca://255idcVME:m34.VAL"
    assert kb.vert.upstream.user_setpoint.source == "mock+ca://255idcVME:m35.VAL"
    assert kb.vert.downstream.user_setpoint.source == "mock+ca://255idcVME:m36.VAL"
    # Check the transforms
    assert (
        kb.horiz.drive_transform.channel_B.input_pv.source
        == "mock+ca://255idcVME:LongKB_CdnH:Drive.INPB"
    )
    assert (
        kb.horiz.readback_transform.channel_B.input_pv.source
        == "mock+ca://255idcVME:LongKB_CdnH:Readback.INPB"
    )
