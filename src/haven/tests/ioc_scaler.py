#!/usr/bin/env python3
from caproto.server import PVGroup, SubGroup, ioc_arg_parser, pvproperty, run
from ophyd.tests.scaler_ioc import EpicsScalerGroup


class SpectroscopyScalerGroup(EpicsScalerGroup):
    offset_start = pvproperty(value=0, name="_offset_start.PROC")
    offset_time = pvproperty(value=5.0, name="_offset_time.VAL")

    class CalcsGroup(PVGroup):
        calc1 = pvproperty(value=2.35, name="_calc1.VAL", dtype=float)
        calc2 = pvproperty(value=2.35, name="_calc2.VAL", dtype=float)
        calc3 = pvproperty(value=2.35, name="_calc3.VAL", dtype=float)
        calc4 = pvproperty(value=2.35, name="_calc4.VAL", dtype=float)
        calc5 = pvproperty(value=2.35, name="_calc5.VAL", dtype=float)
        calc6 = pvproperty(value=2.35, name="_calc6.VAL", dtype=float)
        calc7 = pvproperty(value=2.35, name="_calc7.VAL", dtype=float)
        calc8 = pvproperty(value=2.35, name="_calc8.VAL", dtype=float)

    calcs = SubGroup(CalcsGroup, prefix="")

    class OffsetsGroup(PVGroup):
        offset1 = pvproperty(value=500000, name="_offset0.A", dtype=int)
        offset2 = pvproperty(value=500000, name="_offset0.B", dtype=int)
        offset3 = pvproperty(value=500000, name="_offset0.C", dtype=int)
        offset4 = pvproperty(value=500000, name="_offset0.D", dtype=int)
        offset5 = pvproperty(value=500000, name="_offset1.A", dtype=int)
        offset6 = pvproperty(value=500000, name="_offset1.B", dtype=int)
        offset7 = pvproperty(value=500000, name="_offset1.C", dtype=int)
        offset8 = pvproperty(value=500000, name="_offset1.D", dtype=int)
        offset9 = pvproperty(value=500000, name="_offset2.A", dtype=int)
        offset10 = pvproperty(value=500000, name="_offset2.B", dtype=int)
        offset11 = pvproperty(value=500000, name="_offset2.C", dtype=int)
        offset12 = pvproperty(value=500000, name="_offset2.D", dtype=int)
        offset13 = pvproperty(value=500000, name="_offset3.A", dtype=int)
        offset14 = pvproperty(value=500000, name="_offset3.B", dtype=int)
        offset15 = pvproperty(value=500000, name="_offset3.C", dtype=int)
        offset16 = pvproperty(value=500000, name="_offset3.D", dtype=int)
        offset17 = pvproperty(value=500000, name="_offset4.A", dtype=int)
        offset18 = pvproperty(value=500000, name="_offset4.B", dtype=int)
        offset19 = pvproperty(value=500000, name="_offset4.C", dtype=int)
        offset20 = pvproperty(value=500000, name="_offset4.D", dtype=int)
        offset21 = pvproperty(value=500000, name="_offset5.A", dtype=int)
        offset22 = pvproperty(value=500000, name="_offset5.B", dtype=int)
        offset23 = pvproperty(value=500000, name="_offset5.C", dtype=int)
        offset24 = pvproperty(value=500000, name="_offset5.D", dtype=int)
        offset25 = pvproperty(value=500000, name="_offset6.A", dtype=int)
        offset27 = pvproperty(value=500000, name="_offset6.B", dtype=int)
        offset27 = pvproperty(value=500000, name="_offset6.C", dtype=int)
        offset28 = pvproperty(value=500000, name="_offset6.D", dtype=int)
        offset29 = pvproperty(value=500000, name="_offset7.A", dtype=int)
        offset30 = pvproperty(value=500000, name="_offset7.B", dtype=int)
        offset31 = pvproperty(value=500000, name="_offset7.C", dtype=int)
        offset32 = pvproperty(value=500000, name="_offset7.D", dtype=int)

    offsets = SubGroup(OffsetsGroup, prefix="")

    class NetChannelsGroup(PVGroup):
        net1 = pvproperty(value=20000000, name="_netA.A", dtype=int)
        net2 = pvproperty(value=20000000, name="_netA.B", dtype=int)
        net3 = pvproperty(value=20000000, name="_netA.C", dtype=int)
        net4 = pvproperty(value=20000000, name="_netA.D", dtype=int)
        net5 = pvproperty(value=20000000, name="_netA.E", dtype=int)
        net6 = pvproperty(value=20000000, name="_netA.F", dtype=int)
        net7 = pvproperty(value=20000000, name="_netA.G", dtype=int)
        net8 = pvproperty(value=20000000, name="_netA.H", dtype=int)
        net9 = pvproperty(value=20000000, name="_netA.I", dtype=int)
        net10 = pvproperty(value=20000000, name="_netA.J", dtype=int)
        net11 = pvproperty(value=20000000, name="_netA.K", dtype=int)
        net12 = pvproperty(value=20000000, name="_netA.L", dtype=int)
        net13 = pvproperty(value=20000000, name="_netB.A", dtype=int)
        net14 = pvproperty(value=20000000, name="_netB.B", dtype=int)
        net15 = pvproperty(value=20000000, name="_netB.C", dtype=int)
        net16 = pvproperty(value=20000000, name="_netB.D", dtype=int)
        net17 = pvproperty(value=20000000, name="_netB.E", dtype=int)
        net18 = pvproperty(value=20000000, name="_netB.F", dtype=int)
        net19 = pvproperty(value=20000000, name="_netB.G", dtype=int)
        net20 = pvproperty(value=20000000, name="_netB.H", dtype=int)
        net21 = pvproperty(value=20000000, name="_netB.I", dtype=int)
        net22 = pvproperty(value=20000000, name="_netB.J", dtype=int)
        net23 = pvproperty(value=20000000, name="_netB.K", dtype=int)
        net24 = pvproperty(value=20000000, name="_netB.L", dtype=int)
        net25 = pvproperty(value=20000000, name="_netC.A", dtype=int)
        net26 = pvproperty(value=20000000, name="_netC.B", dtype=int)
        net27 = pvproperty(value=20000000, name="_netC.C", dtype=int)
        net28 = pvproperty(value=20000000, name="_netC.D", dtype=int)
        net29 = pvproperty(value=20000000, name="_netC.E", dtype=int)
        net30 = pvproperty(value=20000000, name="_netC.F", dtype=int)
        net31 = pvproperty(value=20000000, name="_netC.G", dtype=int)
        net32 = pvproperty(value=20000000, name="_netC.H", dtype=int)

    nets = SubGroup(NetChannelsGroup, prefix="")


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="255idVME:scaler1", desc="haven.tests.ioc_scaler test IOC"
    )
    ioc = SpectroscopyScalerGroup(**ioc_options)
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
