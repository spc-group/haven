#!/usr/bin/env python3
from caproto import ChannelType
from caproto.server import PVGroup, SubGroup, ioc_arg_parser, pvproperty, run, PvpropertyInteger

from ophyd.tests.scaler_ioc import EpicsScalerGroup


class AreaDetectorGroup(PVGroup):
    """An IOC matching an EPICS area detector.

    Currently does not describe a full area detector setup. It is just
    meant to provide the bare essentials.

    """

    class CameraGroup(PVGroup):

        acquire_rbv = pvproperty(
            value=0, name="Acquire_RBV", dtype=PvpropertyInteger
        )
        acquire = pvproperty(value=0, name="Acquire", dtype=PvpropertyInteger)
        acquire_busy = pvproperty(
            value=0, name="AcquireBusy", dtype=PvpropertyInteger
        )
        gain = pvproperty(value=10, name="Gain")
        gain_rbv = pvproperty(value=10, name="Gain_RBV")

    cam = SubGroup(CameraGroup, prefix="cam1:")


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="255idSimDet:", desc="haven.tests.ioc_area_detector test IOC"
    )
    ioc = AreaDetectorGroup(**ioc_options)
    run(ioc.pvdb, **run_options)
