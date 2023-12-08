#!/usr/bin/env python3

import logging
from functools import partial

import numpy as np
from caproto import ChannelType
from caproto.server import (
    PVGroup,
    SubGroup,
    get_pv_pair_wrapper,
    ioc_arg_parser,
    pvproperty,
    run,
)
from ophyd.tests.mca_ioc import EpicsDXPGroup, EpicsMCAGroup, MCAROIGroup
from peakutils.peak import gaussian

pvproperty_with_rbv = get_pv_pair_wrapper(setpoint_suffix="", readback_suffix="_RBV")
unknown = int


log = logging.getLogger(__name__)


class DXPGroup(EpicsDXPGroup):
    mca_bin_width = pvproperty(
        value=0.03, name="MCABinWidth_RBV", dtype=float, read_only=True
    )


class ROIGroup(MCAROIGroup):
    # is_hinted = pvproperty(name="BH", dtype=bool)
    hi_chan = pvproperty(name="HI", value=2048)
    lo_chan = pvproperty(name="LO", value=0)
    # hi_chan = pvproperty(name="HI", dtype=int, value=2048)
    # lo_chan = pvproperty(name="LO", dtype=int, value=0)


class MCAGroup(EpicsMCAGroup):
    RoisGroup = type(
        "RoisGroup",
        (PVGroup,),
        {f"roi{i}": SubGroup(ROIGroup, prefix=f".R{i}") for i in range(32)},
    )

    HintsGroup = type(
        "HintsGroup",
        (PVGroup,),
        {
            f"hint{i}": pvproperty(name=f"_R{i}BH", dtype=bool, value="Off")
            for i in range(32)
        },
    )

    rois = SubGroup(RoisGroup, prefix="")
    bluesky_hints = SubGroup(HintsGroup, prefix="")

    erase = pvproperty(name="Erase", dtype=unknown)
    start = pvproperty(name="Start", dtype=unknown)
    preset_real_time = pvproperty(name=".PRTM", value=1.0, dtype=float)
    preset_live_time = pvproperty(name=".PLTM", value=1.0, dtype=float)

    _accumulated_spectrum = None
    spectrum_shape = (2048,)

    @erase.startup
    async def erase(self, instance, async_lib):
        await self.erase.write(1)

    @erase.putter
    async def erase(self, instance, value):
        if value == 1:
            zeros = np.zeros(shape=self.spectrum_shape)
            self._accumulated_spectrum = zeros
            # await self.spectrum.write(self._accumulated_spectrum)

    @start.startup
    async def start(self, instance, async_lib):
        self._async_lib = async_lib

    @start.putter
    async def start(self, instance, value):
        # Wait for the preset time to expire
        await self._async_lib.library.sleep(self.preset_real_time.value)
        # Set a simulated spectrum
        spectrum = self._generate_spectrum()
        await self.spectrum.write(spectrum)

    def _generate_spectrum(self):
        bin_width = self.parent.dxp1.mca_bin_width.value
        shape = self.spectrum_shape
        energies = np.arange(*shape) * bin_width
        # Empty spectrum
        spectrum = np.zeros(shape)
        # Add peaks
        peaks = [
            (8.047, 100, 0.2),  # Cu Ka1
            (8.905, 50, 0.2),  # Cu Kb
            (22.163, 150, 0.5),  # Ag Ka
            (24.942, 75, 0.5),  # Ag Kb
            (49.128, 20, 0.7),  # Er Ka
            (55.681, 10, 0.7),  # Er Kb
        ]
        for energy, height, sigma in peaks:
            height *= np.random.rand() * 0.2 + 0.9
            energy *= np.random.rand() * 0.05 + 0.975
            sigma *= np.random.rand() * 0.2 + 0.9
            spectrum += gaussian(energies, height, energy, sigma)
        # Add noise
        spectrum += 3 * np.random.rand(*shape)
        # Add it to the list of accumulated spectra
        self._accumulated_spectrum += spectrum
        return self._accumulated_spectrum

    spectrum = pvproperty(name="", dtype=float, read_only=True, value=np.zeros((2048,)))


class VortexME4IOC(PVGroup):
    async def propogate_to_mcas(self, instance, value, field):
        """Share this value with all the elements in the detector."""
        # print(f"Propogating {value} to {field} (async_lib: {self._async_lib}.")
        mcas = [self.mca1, self.mca2, self.mca3, self.mca4]
        coroutines = [getattr(mca, field).write(value) for mca in mcas]
        await self._async_lib.library.gather(*coroutines)

    mca1 = SubGroup(MCAGroup, prefix="mca1")
    mca2 = SubGroup(MCAGroup, prefix="mca2")
    mca3 = SubGroup(MCAGroup, prefix="mca3")
    mca4 = SubGroup(MCAGroup, prefix="mca4")
    dxp1 = SubGroup(DXPGroup, prefix="dxp1:")
    dxp2 = SubGroup(DXPGroup, prefix="dxp2:")
    dxp3 = SubGroup(DXPGroup, prefix="dxp3:")
    dxp4 = SubGroup(DXPGroup, prefix="dxp4:")

    start_all = pvproperty(
        name="StartAll",
        dtype=unknown,
        # value="Done",
        # record="mbbi",
        # enum_strings=("Done", "Start"),
        # dtype=ChannelType.ENUM,
    )
    erase_start = pvproperty(name="EraseStart", dtype=unknown)  # value="Done",
    # record="mbbi",
    # enum_strings=("Done", "Start"),
    # dtype=ChannelType.ENUM)
    erase_all = pvproperty(name="EraseAll", dtype=unknown)
    stop_all = pvproperty(name="StopAll", dtype=unknown)
    acquiring = pvproperty(
        name="Acquiring",
        record="mbbi",
        value="Done",
        enum_strings=("Done", "Acquiring"),
        dtype=ChannelType.ENUM,
    )
    preset_real_time = pvproperty(
        name="PresetReal",
        value=1.0,
        dtype=float,
        put=partial(propogate_to_mcas, field="preset_real_time"),
    )
    preset_live_time = pvproperty(
        name="PresetLive",
        value=1.0,
        dtype=float,
        put=partial(propogate_to_mcas, field="preset_live_time"),
    )
    dead_time = pvproperty(name="DeadTime", dtype=float, read_only=True)

    @start_all.startup
    async def start_all(self, instance, async_lib):
        self._async_lib = async_lib

    @start_all.putter
    async def start_all(self, instance, value):
        """Start all the elements in the detector."""
        log.debug(f"Received start_all value: {value}")
        if value in ("Done", 0):
            # No-op for setting "Done"
            return
        await self.acquiring.write("Acquiring")
        await self.propogate_to_mcas(instance, value, field="start")
        # await self._async_lib.library.sleep(self.preset_real_time.value)
        dead_time = np.random.rand() * 30 + 5
        await self.dead_time.write(dead_time)
        await self.acquiring.write("Done")

    @erase_start.putter
    async def erase_start(self, instance, value):
        log.debug(f"Erase-starting: {value}")
        await self.erase_all.write(value)
        await self.start_all.write(value)

    @erase_all.putter
    async def erase_all(self, instance, value):
        log.debug(f"Erasing all: {value}")
        await self.propogate_to_mcas(instance, value, field="erase")


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="vortex_me4:", desc="ophyd.tests.test_mca test IOC"
    )
    ioc = VortexME4IOC(**ioc_options)
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
