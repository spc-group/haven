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

    E.g. "25idcVME:m1.VAL"

    """

    m1 = pvproperty(value=5000.0, doc="SLT V Upper", record=ResponsiveMotorFields)
    m2 = pvproperty(value=5000.0, doc="SLT V Lower", record=ResponsiveMotorFields)
    m3 = pvproperty(value=5000.0, doc="SLT H Inb", record=ResponsiveMotorFields)

    default_prefix = "vme_crate_ioc:"


if __name__ == '__main__':
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
