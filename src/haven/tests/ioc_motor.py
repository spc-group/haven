#!/usr/bin/env python3
from caproto.server import PVGroup, ioc_arg_parser, pvproperty, run

from haven.simulated_ioc import ResponsiveMotorFields


class MotorGroup(PVGroup):
    """
    An IOC with some motor records, similar to those found in a VME crate.

    E.g. "25idcVME:m1.VAL"

    """

    m1 = pvproperty(value=5000.0, doc="SLT V Upper", record=ResponsiveMotorFields)
    m2 = pvproperty(value=5000.0, doc="SLT V Lower", record=ResponsiveMotorFields)
    m3 = pvproperty(value=5000.0, doc="SLT H Inb", record=ResponsiveMotorFields)
    m4 = pvproperty(value=5000.0, doc="SLT H Otb", record=ResponsiveMotorFields)


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="225idVME:", desc="haven.tests.ioc_motor test IOC"
    )
    ioc = MotorGroup(**ioc_options)
    run(ioc.pvdb, **run_options)
