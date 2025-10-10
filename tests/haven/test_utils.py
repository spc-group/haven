from haven import sanitize_name


def test_sanitize_name():
    assert (
        sanitize_name("high_heat_load_mirror_1-transverse")
        == "high_heat_load_mirror_1_transverse"
    )
    assert (
        sanitize_name("high_heat_load_mirror_1.transverse")
        == "high_heat_load_mirror_1_transverse"
    )


def test_sanitize_name_with_spaces():
    # Some devices use the .DESC field, might have spaces, too
    assert sanitize_name("Det InOut") == "Det_InOut"
