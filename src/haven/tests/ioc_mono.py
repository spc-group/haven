#!/usr/bin/env python3
from caproto.server import PVGroup, ioc_arg_parser, pvproperty, run

from haven.simulated_ioc import ResponsiveMotorFields  # , IOC as IOC_


class MonoGroup(PVGroup):
    """
    An IOC with a monochromator.

    """

    m1 = pvproperty(value=0, doc="horiz", name="ACS:m1", record=ResponsiveMotorFields)
    m2 = pvproperty(value=0, doc="vert", name="ACS:m2", record=ResponsiveMotorFields)
    m3 = pvproperty(value=0, doc="bragg", name="ACS:m3", record=ResponsiveMotorFields)
    m4 = pvproperty(value=0, doc="gap", name="ACS:m4", record=ResponsiveMotorFields)
    m5 = pvproperty(value=0, doc="roll2", name="ACS:m5", record=ResponsiveMotorFields)
    m6 = pvproperty(value=0, doc="pitch2", name="ACS:m6", record=ResponsiveMotorFields)
    m7 = pvproperty(
        value=0, doc="roll-int", name="ACS:m7", record=ResponsiveMotorFields
    )
    m8 = pvproperty(value=0, doc="pi-int", name="ACS:m8", record=ResponsiveMotorFields)
    Energy = pvproperty(value=10000.0, doc="Energy", record=ResponsiveMotorFields)
    Offset = pvproperty(value=9009, doc="Offset", record=ResponsiveMotorFields)
    mode = pvproperty(value=1, doc="mode", record=ResponsiveMotorFields)
    id_tracking = pvproperty(value=0, name="ID_tracking", doc="IDTracking")
    id_offset = pvproperty(value=0, name="ID_offset", doc="ID offset")
    dspacing = pvproperty(value=3.135, doc="Crystal d-spacing", dtype=float)
    EnergyC1 = pvproperty(value=1, name="EnergyC1.VAL", dtype=float)
    EnergyC2 = pvproperty(value=1, name="EnergyC2.VAL", dtype=float)
    EnergyC3 = pvproperty(value=1, name="EnergyC3.VAL", dtype=float)


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="255idMono:", desc="haven.tests.ioc_mono test IOC"
    )
    ioc = MonoGroup(**ioc_options)
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
