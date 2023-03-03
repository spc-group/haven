#!/usr/bin/env python3

from caproto.server import (
    pvproperty,
    run,
    PvpropertyDouble,
)

from haven.simulated_ioc import ResponsiveMotorFields, IOC as IOC_


class IOC(IOC_):
    """
    An IOC that looks like an undulator.

    E.g. "25IDds:Energy"

    """

    ScanEnergy = pvproperty(value=0, doc="ID Energy Scan Input", dtype=PvpropertyDouble)
    Energy = pvproperty(
        value=0, doc="", record=ResponsiveMotorFields, dtype=PvpropertyDouble
    )
    Busy = pvproperty(value=0, doc="", name="Busy.VAL")
    Stop = pvproperty(value=0, doc="", name="Stop.VAL")

    default_prefix = "id_ioc:"


if __name__ == "__main__":
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
