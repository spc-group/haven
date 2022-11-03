#!/usr/bin/env python3
from textwrap import dedent

from caproto import ChannelType
from caproto.server import (
    pvproperty,
    run,
    PvpropertyDouble,
)

from haven.simulated_ioc import ResponsiveMotorFields, ioc_arg_parser, IOC as IOC_


class IOC(IOC_):
    """An IOC with an SR570 pre-amplifier.

    E.g.

    - 25idc:SR01:IpreSlit:sens_num.VAL"
    - 25idc:SR01:IpreSlit:sens_unit.VAL

    """

    sens_num = pvproperty(
        value="5",
        enum_strings=["1", "2", "5", "10", "20", "50", "100", "200", "500"],
        record="mbbi",
        dtype=ChannelType.ENUM,
    )
    sens_unit = pvproperty(
        value="nA/V",
        enum_strings=["pA/V", "nA/V", "uA/V", "mA/V"],
        record="mbbi",
        dtype=ChannelType.ENUM,
    )

    default_prefix = "preamp_ioc:"


if __name__ == '__main__':
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
