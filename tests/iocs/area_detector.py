#!/usr/bin/env python3

from caproto.server import (
    pvproperty,
    PvpropertyInteger,
    run,
)

from haven.simulated_ioc import ResponsiveMotorFields, IOC as IOC_


class IOC(IOC_):
    """
    An IOC with some motor records, similar to those found in a VME crate.

    E.g. "25idcVME:m1.VAL"

    """

    cam1_acquire_rbv = pvproperty(value=0, name="cam1:Acquire_RBV", dtype=PvpropertyInteger)
    cam1_acquire = pvproperty(value=0, name="cam1:Acquire", dtype=PvpropertyInteger)
    cam1_acquire_busy = pvproperty(value=0, name="cam1:AcquireBusy", dtype=PvpropertyInteger)
    default_prefix = "99idSimDet:"


if __name__ == "__main__":
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
