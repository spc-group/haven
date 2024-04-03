#!/usr/bin/env python3
from caproto.server import PVGroup, PvpropertyDouble, ioc_arg_parser, pvproperty, run

from haven.simulated_ioc import ResponsiveMotorFields  # , IOC as IOC_


class UndulatorGroup(PVGroup):
    """
    An IOC that looks like an undulator.

    E.g. "25IDds:Energy"

    """

    ScanEnergy = pvproperty(value=0, doc="ID Energy Scan Input", dtype=PvpropertyDouble)
    Energy = pvproperty(
        value=0,
        doc="",
        record=ResponsiveMotorFields,
        dtype=PvpropertyDouble,
    )
    Busy = pvproperty(value=0, doc="", name="Busy")
    Stop = pvproperty(value=0, doc="", name="Stop")
    Gap = pvproperty(value=0, doc="", name="Gap")
    TaperEnergy = pvproperty(value=0, doc="")
    TaperGap = pvproperty(value=0, doc="")
    Start = pvproperty(value=0, doc="")
    HarmonicValue = pvproperty(value=0, doc="")
    DeadbandGap = pvproperty(value=0, doc="")
    DeviceLimit = pvproperty(value=0, doc="")
    AccessSecurity = pvproperty(value=0, doc="")
    TotalPower = pvproperty(value=0, doc="")
    Message1 = pvproperty(value=0, doc="")
    Message2 = pvproperty(value=0, doc="")
    Message3 = pvproperty(value=0, doc="")
    ShClosedTime = pvproperty(value=0, doc="")
    Device = pvproperty(value=0, doc="")
    Location = pvproperty(value=0, doc="")
    Version = pvproperty(value=0, doc="")


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="ID255:", desc="haven.tests.ioc_undulator test IOC"
    )
    ioc = UndulatorGroup(**ioc_options)
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
