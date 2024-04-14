"""Ophyd device support for a set of XIA PFCU-controlled filters.

A PFCUFilterBank controls a set of 4 filters. Optionally, 2 filters in
a filter bank can be used as a shutter.

"""
from ophyd import PVPositioner

class PFCUFilter(PVPositioner):
    """A single filter in a PFCU filter bank.

    E.g. 25idc:pfcu0:filter1_mat
    """
    material = Cpt("_mat", kind="config")
    thickness = Cpt("_thick", kind="config")
    notes = Cpt("_other", kind="config")
    setpoint = Cpt("", kind="normal")
    readback = Cpt("_RBV", kind="normal")


class PFCUFilterBank(PVPositioner):
    filter1 = Cpt(PFCUFilter, "filter1")
    filter2 = Cpt(PFCUFilter, "filter2")
    filter3 = Cpt(PFCUFilter, "filter3")
    filter4 = Cpt(PFCUFilter, "filter4")
    setpoint = Cpt("config")
    readback = Cpt("config_RBV")


