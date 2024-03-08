from firefly.iocs import IocsDisplay

dummy_config = {"iocs"}


def test_embedded_display_widgets(qtbot, ffapp):
    """Test the the voltmeters creates a new embedded display widget for
    each ion chamber.

    """
    # Load the display
    display = IocsDisplay()
    # Check that the embedded display widgets get added correctly
    assert hasattr(display, "_ioc_displays")
    assert len(display._ioc_displays) == 2
    # two displays and a separator
    assert display.iocs_layout.count() == 3
    # Check that the embedded display widgets have the correct macros
    emb_disp = display._ioc_displays[0]
    disp = emb_disp.open_file(force=True)
    macros = disp.macros()
    assert macros == {"NAME": "255idb", "IOC": "glados:ioc255idb"}
