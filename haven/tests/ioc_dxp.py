#!/usr/bin/env python3
from caproto.server import (
    PVGroup,
    SubGroup,
    get_pv_pair_wrapper,
    ioc_arg_parser,
    pvproperty,
    run,
)
from ophyd.tests.mca_ioc import EpicsMCAGroup, EpicsDXPGroup, MCAROIGroup

pvproperty_with_rbv = get_pv_pair_wrapper(setpoint_suffix="", readback_suffix="_RBV")
unknown = int


class ROIGroup(MCAROIGroup):
    is_hinted = pvproperty(name="BH", dtype=bool)


class MCAGroup(EpicsMCAGroup):
    # class RoisGroup(PVGroup):
    #     roi0 = SubGroup(ROIGroup, prefix=".R0")
    RoisGroup = type("RoisGroup", (PVGroup,),
                     {f"roi{i}": SubGroup(ROIGroup, prefix=f".R{i}") for i in range(32)})

    rois = SubGroup(RoisGroup, prefix="")        


class VortexME4IOC(PVGroup):
    mca1 = SubGroup(MCAGroup, prefix="mca1")
    mca2 = SubGroup(MCAGroup, prefix="mca2")
    mca3 = SubGroup(MCAGroup, prefix="mca3")
    mca4 = SubGroup(MCAGroup, prefix="mca4")
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
