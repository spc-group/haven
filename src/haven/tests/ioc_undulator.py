#!/usr/bin/env python3
from caproto import ChannelType
from caproto.server import (
    PVGroup,
    SubGroup,
    ioc_arg_parser,
    pvproperty,
    run,
    PvpropertyDouble,
)
from ophyd.tests.fake_motor_ioc import FakeMotorIOC

from haven.simulated_ioc import ResponsiveMotorFields  # , IOC as IOC_


class UndulatorGroup(PVGroup):

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


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="255ID:", desc="haven.tests.ioc_undulator test IOC"
    )
    ioc = UndulatorGroup(**ioc_options)
    run(ioc.pvdb, **run_options)
