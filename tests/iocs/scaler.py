#!/usr/bin/env python3
from textwrap import dedent

from caproto.server import (
    pvproperty,
    run,
    PvpropertyDouble,
)

from haven.simulated_ioc import ResponsiveMotorFields, ioc_arg_parser, IOC as IOC_


class IOC(IOC_):
    """An IOC mimicing a scaler connected to a VME crate."""

    S2 = pvproperty(name=".S2", value=21000000, doc="It")
    CNT = pvproperty(name=".CNT", value=1)
    TP = pvproperty(name=".TP", value=1.)
    calc2 = pvproperty(name="_calc2.VAL", value=2.35)

    default_prefix = "vme_crate_ioc"


if __name__ == '__main__':
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
