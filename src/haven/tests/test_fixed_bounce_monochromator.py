from haven.devices import FixedBounceMonochromator


async def test_signals():
    mono = FixedBounceMonochromator(prefix="25idcVME:Si220:", name="secondary_mono")
    await mono.connect(mock=True)
    reading = await mono.read()
    # Check the reading signals
    assert set(reading.keys()) == {
        "secondary_mono-energy",
        "secondary_mono-bragg",
        "secondary_mono-beam_offset",
    }
    # Hinted signals
    assert set(mono.hints["fields"]) == {
        "secondary_mono-energy",
        "secondary_mono-bragg",
    }
    # Now for the configuration
    config = await mono.read_configuration()
    assert set(config.keys()) == {
        "secondary_mono-bragg-description",
        "secondary_mono-bragg-motor_egu",
        "secondary_mono-bragg-offset",
        "secondary_mono-bragg-offset_dir",
        "secondary_mono-bragg-velocity",
        "secondary_mono-d_spacing",
        "secondary_mono-gap",
        "secondary_mono-bragg_direction",
        "secondary_mono-bragg_offset",
        "secondary_mono-energy-description",
        "secondary_mono-energy-motor_egu",
        "secondary_mono-energy-offset",
        "secondary_mono-energy-offset_dir",
        "secondary_mono-energy-velocity",
    }
