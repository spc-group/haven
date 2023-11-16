#!/usr/bin/env python3
from caproto.server import PVGroup, ioc_arg_parser, pvproperty, run


class SimpleGroup(PVGroup):
    """
    An IOC with three uncoupled read/writable PVs

    Scalar PVs
    ----------
    A (int)
    B (float)

    Vectors PVs
    -----------
    C (vector of int)
    """

    A = pvproperty(value=1, doc="An integer")
    B = pvproperty(value=2.0, doc="A float")
    C = pvproperty(value=[1, 2, 3], doc="An array of integers")


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="simple:", desc="haven.tests.ioc_undulator test IOC"
    )
    ioc = SimpleGroup(**ioc_options)
    run(ioc.pvdb, **run_options)
