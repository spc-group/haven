#!/usr/bin/env python3
from caproto.server import PVGroup, ioc_arg_parser, pvproperty, run

from haven.simulated_ioc import ResponsiveMotorFields


class MotorGroup(PVGroup):
    """
    An IOC with some motor records, similar to those found in a VME crate.

    E.g. "25idcVME:m1.VAL"

    """

    m1 = pvproperty(value=5000.0, doc="SLT V Upper", record=ResponsiveMotorFields)
    m2 = pvproperty(value=5000.0, doc="SLT V Lower", record=ResponsiveMotorFields)
    m3 = pvproperty(value=5000.0, doc="SLT H Inb", record=ResponsiveMotorFields)
    m4 = pvproperty(value=5000.0, doc="SLT H Otb", record=ResponsiveMotorFields)


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="225idVME:", desc="haven.tests.ioc_motor test IOC"
    )
    ioc = MotorGroup(**ioc_options)
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
