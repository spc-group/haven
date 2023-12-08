#!/usr/bin/env python3
from caproto import ChannelType
from caproto.server import PVGroup, SubGroup, ioc_arg_parser, pvproperty, run


class PreampsGroup(PVGroup):
    class PreampGroup(PVGroup):
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
        offset_num = pvproperty(
            value="5",
            enum_strings=["1", "2", "5", "10", "20", "50", "100", "200", "500"],
            record="mbbi",
            dtype=ChannelType.ENUM,
        )
        offset_unit = pvproperty(
            value="nA",
            enum_strings=["pA", "nA", "uA", "mA"],
            record="mbbi",
            dtype=ChannelType.ENUM,
        )
        set_all = pvproperty(value=1, name="init.PROC", doc="")

    preamp1 = SubGroup(PreampGroup, prefix="SR01:")
    preamp2 = SubGroup(PreampGroup, prefix="SR02:")
    preamp3 = SubGroup(PreampGroup, prefix="SR03:")
    preamp4 = SubGroup(PreampGroup, prefix="SR04:")


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="255idc:", desc="haven.tests.ioc_preamp test IOC"
    )
    ioc = PreampsGroup(**ioc_options)
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
