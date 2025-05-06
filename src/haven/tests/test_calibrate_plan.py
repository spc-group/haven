from haven.plans import calibrate


async def test_offset_value(mono):
    msgs = list(calibrate(mono.energy, truth=8703, dial=8700))
    assert len(msgs) == 1
    msg = msgs[0]
    assert msg.obj is mono.energy
