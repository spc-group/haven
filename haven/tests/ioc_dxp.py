#!/usr/bin/env python3
from caproto.server import (
    PVGroup,
    SubGroup,
    get_pv_pair_wrapper,
    ioc_arg_parser,
    pvproperty,
    run,
)
from ophyd.tests.mca_ioc import EpicsMCAGroup, EpicsDXPGroup

pvproperty_with_rbv = get_pv_pair_wrapper(setpoint_suffix="", readback_suffix="_RBV")
unknown = int


class VortexME4IOC(PVGroup):
    mca1 = SubGroup(EpicsMCAGroup, prefix="mca1")
    mca2 = SubGroup(EpicsMCAGroup, prefix="mca2")
    mca3 = SubGroup(EpicsMCAGroup, prefix="mca3")
    mca4 = SubGroup(EpicsMCAGroup, prefix="mca4")
    dxp = SubGroup(EpicsDXPGroup, prefix="dxp:")

    start_all = pvproperty(name="StartAll", dtype=unknown)
    erase_all = pvproperty(name="EraseAll", dtype=unknown)
    erase_start = pvproperty(name="EraseStart", dtype=unknown)
    stop_all = pvproperty(name="StopAll", dtype=unknown)


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="vortex_me4:", desc="ophyd.tests.test_mca test IOC"
    )
    ioc = VortexME4IOC(**ioc_options)
    run(ioc.pvdb, **run_options)
