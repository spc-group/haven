#!/usr/bin/env python3

from caproto.server import (
    pvproperty,
    run,
)

from haven.simulated_ioc import ResponsiveMotorFields, IOC as IOC_


class IOC(IOC_):
    """
    An IOC with a monochromator.

    """

    m1 = pvproperty(value=0, doc="horiz", name="ACS:m1", record=ResponsiveMotorFields)
    m2 = pvproperty(value=0, doc="vert", name="ACS:m2", record=ResponsiveMotorFields)
    m3 = pvproperty(value=0, doc="bragg", name="ACS:m3", record=ResponsiveMotorFields)
    m4 = pvproperty(value=0, doc="gap", name="ACS:m4", record=ResponsiveMotorFields)
    m5 = pvproperty(value=0, doc="roll2", name="ACS:m5", record=ResponsiveMotorFields)
    m6 = pvproperty(value=0, doc="pitch2", name="ACS:m6", record=ResponsiveMotorFields)
    m7 = pvproperty(
        value=0, doc="roll-int", name="ACS:m7", record=ResponsiveMotorFields
    )
    m8 = pvproperty(value=0, doc="pi-int", name="ACS:m8", record=ResponsiveMotorFields)
    Energy = pvproperty(value=10000.0, doc="Energy", record=ResponsiveMotorFields)
    Offset = pvproperty(value=9009, doc="Offset", record=ResponsiveMotorFields)
    mode = pvproperty(value=1, doc="mode", record=ResponsiveMotorFields)
    id_offset = pvproperty(value=0, doc="ID offset", name="ID_offset")

    default_prefix = "mono_ioc:"


if __name__ == "__main__":
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
