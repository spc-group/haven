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
