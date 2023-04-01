#!/usr/bin/env python3

from caproto.server import (
    pvproperty,
    run,
)

from haven.simulated_ioc import ResponsiveMotorFields, IOC as IOC_


class IOC(IOC_):
    """
    An IOC for a PTC10 temperature controller.

    """

    tc_temperature = pvproperty(
        value=0, doc="Temperature from thermocouple", name="2A:temperature"
    )
    pid_setpoint = pvproperty(value=0, doc="", name="5A:setPoint")
    pid_setpoint_rbv = pvproperty(value=0, doc="", name="5A:setPoint_RBV")
    pid_voltage = pvproperty(value=0, doc="", name="5A:output")
    pid_voltage_rbv = pvproperty(value=0, doc="", name="5A:output_RBV")
    pid_highlimit = pvproperty(value=0, doc="", name="5A:highLimit")
    pid_highlimit_rbv = pvproperty(value=0, doc="", name="5A:highLimit_RBV")
    pid_lowlimit = pvproperty(value=0, doc="", name="5A:lowLimit")
    pid_lowlimit_rbv = pvproperty(value=0, doc="", name="5A:lowLimit_RBV")
    pid_iotype = pvproperty(value=0, doc="", name="5A:ioType")
    pid_iotype_rbv = pvproperty(value=0, doc="", name="5A:ioType_RBV")
    pid_ramprate = pvproperty(value=0, doc="", name="5A:rampRate")
    pid_ramprate_rbv = pvproperty(value=0, doc="", name="5A:rampRate_RBV")
    pid_offswitch = pvproperty(value=0, doc="", name="5A:off")
    pid_pidmode = pvproperty(value=0, doc="", name="5A:pid:mode")
    pid_pidmode_rbv = pvproperty(value=0, doc="", name="5A:pid:mode_RBV")
    pid_P = pvproperty(value=0, doc="", name="5A:pid:P")
    pid_P_rbv = pvproperty(value=0, doc="", name="5A:pid:P_RBV")
    pid_I = pvproperty(value=0, doc="", name="5A:pid:I")
    pid_I_rbv = pvproperty(value=0, doc="", name="5A:pid:I_RBV")
    pid_D = pvproperty(value=0, doc="", name="5A:pid:D")
    pid_D_rbv = pvproperty(value=0, doc="", name="5A:pid:D_RBV")
    pid_inputchoice = pvproperty(value=0, doc="", name="5A:pid:input")
    pid_inputchoice_rbv = pvproperty(value=0, doc="", name="5A:pid:input_RBV")
    pid_tunelag = pvproperty(value=0, doc="", name="5A:tune:lag")
    pid_tunelag_rbv = pvproperty(value=0, doc="", name="5A:tune:lag_RBV")
    pid_tunestep = pvproperty(value=0, doc="", name="5A:tune:step")
    pid_tunestep_rbv = pvproperty(value=0, doc="", name="5A:tune:step_RBV")
    pid_tunemode = pvproperty(value=0, doc="", name="5A:tune:mode")
    pid_tunemode_rbv = pvproperty(value=0, doc="", name="5A:tune:mode_RBV")
    pid_tunetype = pvproperty(value=0, doc="", name="5A:tune:type")
    pid_tunetype_rbv = pvproperty(value=0, doc="", name="5A:tune:type_RBV")

    default_prefix = "ptc10ioc:"


if __name__ == "__main__":
    pvdb, run_options = IOC.parse_args()
    run(pvdb, **run_options)
