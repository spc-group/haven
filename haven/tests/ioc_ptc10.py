#!/usr/bin/env python3
from caproto import ChannelType
from caproto.server import PVGroup, SubGroup, ioc_arg_parser, pvproperty, run

from ophyd.tests.scaler_ioc import EpicsScalerGroup


class PTC10Group(PVGroup):
    """
    An IOC for a PTC10 temperature controller.

    """

    class ThermocoupleGroup(PVGroup):
        temperature = pvproperty(
            value=21.3, doc="Temperature from thermocouple", name="temperature"
        )

    tc1 = SubGroup(ThermocoupleGroup, prefix="2A:")

    class PIDGroup(PVGroup):
        setpoint = pvproperty(value=0, doc="", name="setPoint")
        setpoint_rbv = pvproperty(value=0, doc="", name="setPoint_RBV")
        voltage = pvproperty(value=0, doc="", name="output")
        voltage_rbv = pvproperty(value=0, doc="", name="output_RBV")
        highlimit = pvproperty(value=0, doc="", name="highLimit")
        highlimit_rbv = pvproperty(value=0, doc="", name="highLimit_RBV")
        lowlimit = pvproperty(value=0, doc="", name="lowLimit")
        lowlimit_rbv = pvproperty(value=0, doc="", name="lowLimit_RBV")
        iotype = pvproperty(value=0, doc="", name="ioType")
        iotype_rbv = pvproperty(value=0, doc="", name="ioType_RBV")
        ramprate = pvproperty(value=0, doc="", name="rampRate")
        ramprate_rbv = pvproperty(value=0, doc="", name="rampRate_RBV")
        offswitch = pvproperty(value=0, doc="", name="off")
        pidmode = pvproperty(value=0, doc="", name="pid:mode")
        pidmode_rbv = pvproperty(value=0, doc="", name="pid:mode_RBV")
        P = pvproperty(value=0, doc="", name="pid:P")
        P_rbv = pvproperty(value=0, doc="", name="pid:P_RBV")
        I = pvproperty(value=0, doc="", name="pid:I")
        I_rbv = pvproperty(value=0, doc="", name="pid:I_RBV")
        D = pvproperty(value=0, doc="", name="pid:D")
        D_rbv = pvproperty(value=0, doc="", name="pid:D_RBV")
        inputchoice = pvproperty(value=0, doc="", name="pid:input")
        inputchoice_rbv = pvproperty(value=0, doc="", name="pid:input_RBV")
        tunelag = pvproperty(value=0, doc="", name="tune:lag")
        tunelag_rbv = pvproperty(value=0, doc="", name="tune:lag_RBV")
        tunestep = pvproperty(value=0, doc="", name="tune:step")
        tunestep_rbv = pvproperty(value=0, doc="", name="tune:step_RBV")
        tunemode = pvproperty(value=0, doc="", name="tune:mode")
        tunemode_rbv = pvproperty(value=0, doc="", name="tune:mode_RBV")
        tunetype = pvproperty(value=0, doc="", name="tune:type")
        tunetype_rbv = pvproperty(value=0, doc="", name="tune:type_RBV")

    pid1 = SubGroup(PIDGroup, prefix="5A:")


default_prefix = "ptc10ioc:"

if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="255idptc10:", desc="haven.tests.ioc_ptc10 test IOC"
    )
    ioc = PTC10Group(**ioc_options)
    run(ioc.pvdb, **run_options)
