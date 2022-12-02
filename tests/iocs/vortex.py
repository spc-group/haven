#!/usr/bin/env python3

from caproto.server import (
    pvproperty,
    run,
)

from haven.simulated_ioc import IOC as IOC_


class IOC(IOC_):
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

    NumImages = pvproperty(value=1, doc="Number of images to capture total.")
    TriggerMode = pvproperty(value=1, doc="Operation mode for triggering the detector")
    Acquire = pvproperty(value=0, doc="Acquire the data")
    Erase = pvproperty(
        value=0, doc="Erases the data in preparation for collecting new data"
    )

    default_prefix = "xspress:"


if __name__ == "__main__":
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
