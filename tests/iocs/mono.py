#!/usr/bin/env python3
from textwrap import dedent

from caproto.server import (
    pvproperty,
    run,
    PvpropertyDouble,
)

from haven.simulated_ioc import ResponsiveMotorFields, ioc_arg_parser, IOC as IOC_


class IOC(IOC_):
    """
    An IOC with some motor records, similar to those found in a VME crate.

    """

    m1 = pvproperty(value=0, doc="horiz", record=ResponsiveMotorFields)
    m2 = pvproperty(value=0, doc="vert", record=ResponsiveMotorFields)
    m3 = pvproperty(value=0, doc="bragg", record=ResponsiveMotorFields)
    m4 = pvproperty(value=0, doc="gap", record=ResponsiveMotorFields)
    m5 = pvproperty(value=0, doc="roll2", record=ResponsiveMotorFields)
    m6 = pvproperty(value=0, doc="pitch2", record=ResponsiveMotorFields)
    m7 = pvproperty(value=0, doc="roll-int", record=ResponsiveMotorFields)
    m8 = pvproperty(value=0, doc="pi-int", record=ResponsiveMotorFields)
    Energy = pvproperty(value=10000.0, doc="Energy", record=ResponsiveMotorFields)
    
    default_prefix = "mono_ioc:"


if __name__ == '__main__':
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
