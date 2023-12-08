#!/usr/bin/env python3
from caproto.server import PVGroup, SubGroup, ioc_arg_parser, pvproperty, run


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


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
