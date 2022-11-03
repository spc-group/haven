#!/usr/bin/env python3
from textwrap import dedent

from caproto.server import (
    PVGroup,
    template_arg_parser,
    pvproperty,
    run,
    records,
    PvpropertyDouble,
)

from haven.simulated_ioc import ResponsiveMotorFields, ioc_arg_parser, IOC as IOC_


class IOC(IOC_):
    """
    An IOC that looks like an undulator.

    E.g. "25IDds:Energy"

    """

    ScanEnergy = pvproperty(value=0, doc="ID Energy Scan Input", dtype=PvpropertyDouble)
    Energy = pvproperty(value=0, doc="", record=ResponsiveMotorFields, dtype=PvpropertyDouble)
    Busy = pvproperty(value=0, doc="")
    Stop = pvproperty(value=0, doc="")

    default_prefix = "id_ioc:"


if __name__ == '__main__':
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
