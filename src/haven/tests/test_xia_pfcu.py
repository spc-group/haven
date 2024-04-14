from haven.instrument.xia_pfcu import PFCUFilter, PFCUFilterBank, PFCUFilterShutter


def test_shutter_factory():
    """Check that a shutter device is created if requested."""
    filterbank = PFCUFilterBank(shutters=[(2, 3)])  #
    assert hasattr(filterbank, "shutters")
    assert isinstance(filterbank.shutters.shutter0, PFCUFilterShutter)
    assert hasattr(filterbank, "shutters")
    assert isinstance(filterbank.filters.filter1, PFCUFilter)
    assert isinstance(filterbank.filters.filter4, PFCUFilter)
    assert not hasattr(filterbank.filters, "filter2")
    assert not hasattr(filterbank.filters, "filter3")
