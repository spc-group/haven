from haven.instrument.mirrors import (
    KBMirrors,
    KBMirror,
    load_mirrors,
    HighHeatLoadMirror,
)


def test_high_heat_load_mirror_PVs():
    mirror = HighHeatLoadMirror(prefix="255ida:ORM2:", name="orm2")
    # Check the motor PVs
    assert mirror.transverse.user_readback.pvname == "255ida:ORM2:m1.RBV"
    assert mirror.roll.user_setpoint.pvname == "255ida:ORM2:m2.VAL"
    assert mirror.upstream.user_setpoint.pvname == "255ida:ORM2:m3.VAL"
    assert mirror.downstream.user_setpoint.pvname == "255ida:ORM2:m4.VAL"
    assert mirror.normal.user_setpoint.pvname == "255ida:ORM2:lateral.VAL"
    assert mirror.pitch.user_setpoint.pvname == "255ida:ORM2:coarsePitch.VAL"
    assert mirror.bender.user_setpoint.pvname == "255ida:ORM2:m5.VAL"
    # Check the transform PVs
    assert (
        mirror.drive_transform.channels.B.input_pv.pvname
        == "255ida:ORM2:lats:Drive.INPB"
    )
    assert (
        mirror.readback_transform.channels.B.input_pv.pvname
        == "255ida:ORM2:lats:Readback.INPB"
    )



def test_kb_mirrors_PVs():
    kb = KBMirrors(prefix="255idcVME:LongKB_Cdn:", name="kb")
    # assert not kb.connected
    assert isinstance(kb.vert, KBMirror)
    assert isinstance(kb.horiz, KBMirror)
    # Check PVs
    assert kb.vert.prefix == "255idcVME:LongKB_Cdn:V:"
    # "25idcVME:LongKB_Cdn:H:pitch.VAL"
    assert kb.horiz.pitch.user_setpoint.pvname == "255idcVME:LongKB_Cdn:H:pitch.VAL"
    assert kb.vert.normal.user_setpoint.pvname == "255idcVME:LongKB_Cdn:V:height.VAL"
    # Check the transforms
    assert (
        kb.horiz.drive_transform.channels.B.input_pv.pvname
        == "255idcVME:LongKB_CdnH:Drive.INPB"
    )
    assert (
        kb.horiz.readback_transform.channels.B.input_pv.pvname
        == "255idcVME:LongKB_CdnH:Readback.INPB"
    )


def test_load_mirrors(sim_registry):
    load_mirrors()
    # Check that the KB mirrors were created
    kb_mirrors = sim_registry.find(name="LongKB_Cdn")
    assert isinstance(kb_mirrors, KBMirrors)
    # Check that the HHL mirrors were created
    hhl_mirrors = sim_registry.find(name="ORM1")
    assert isinstance(hhl_mirrors, HighHeatLoadMirror)
