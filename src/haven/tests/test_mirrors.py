from haven.instrument.mirrors import (
    KBMirrors,
    KBMirror,
    load_mirrors,
    HighHeatLoadMirror,
)


# def test_mirror_PVs():
#     mirror = Mirror(prefix="255idcVME:LongKB_Cdn:H:", name="mirror")
#     assert mirror.pitch.user_setpoint.pvname == "255idcVME:LongKB_Cdn:H:pitch.VAL"
#     assert mirror.normal.user_setpoint.pvname == "255idcVME:LongKB_Cdn:H:height.VAL"


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
