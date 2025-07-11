import asyncio
import os
from pathlib import Path

# from pydm.data_plugins import plugin_modules, add_plugin
import pytest
from ophyd import DynamicDeviceComponent as DCpt
from ophyd import Kind
from ophyd.sim import instantiate_fake_device, make_fake_device

import haven
from haven import devices
from haven.devices import Xspress3Detector
from haven.devices.aps import ApsMachine
from haven.devices.beamline_manager import BeamlineManager, IOCManager
from haven.devices.dxp import DxpDetector
from haven.devices.dxp import add_mcas as add_dxp_mcas
from haven.devices.ion_chamber import IonChamber
from haven.devices.robot import Robot
from haven.devices.shutter import PssShutter
from haven.devices.xia_pfcu import PFCUFilter, PFCUFilterBank

top_dir = Path(__file__).parent.resolve()
haven_dir = top_dir / "haven"


# Specify the configuration files to use for testing
os.environ["HAVEN_CONFIG_FILES"] = ",".join(
    [
        f"{haven_dir/'iconfig_testing.toml'}",
        f"{haven_dir/'iconfig_default.toml'}",
    ]
)


@pytest.fixture()
def sim_registry(monkeypatch):
    # Save the registry so we can restore it later
    registry = haven.beamline.devices
    objects_by_name = registry._objects_by_name
    objects_by_label = registry._objects_by_label
    registry.clear()
    registry.use_typhos = False
    # Run the test
    try:
        yield registry
    finally:
        # Restore the previous registry components
        registry.clear()
        registry._objects_by_name = objects_by_name
        registry._objects_by_label = objects_by_label


@pytest.fixture()
async def ion_chamber(sim_registry):
    ion_chamber = IonChamber(
        scaler_prefix="255idcVME:3820:",
        scaler_channel=2,
        preamp_prefix="255idc:SR03",
        voltmeter_prefix="255idc:LJT7_Voltmeter0:",
        voltmeter_channel=1,
        counts_per_volt_second=10e6,
        name="I00",
    )
    # Connect to the ion chamber
    await ion_chamber.connect(mock=True)
    sim_registry.register(ion_chamber)
    return ion_chamber


class SimpleBeamlineManager(BeamlineManager):
    """For a fake class, we need to un-override __new__ to just make
    itself.

    """

    iocs = DCpt(
        {
            "ioc255idb": (IOCManager, "ioc255idb:", {}),
            "ioc255idc": (IOCManager, "ioc255idc:", {}),
        }
    )

    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)


@pytest.fixture()
def beamline_manager(sim_registry):
    """A fake set of slits using the 4-blade setup."""
    FakeManager = make_fake_device(SimpleBeamlineManager)
    manager = FakeManager(
        prefix="companionCube:", name="companion_cube", labels={"beamline_manager"}
    )
    sim_registry.register(manager)
    return manager


class DxpVortex(DxpDetector):
    mcas = DCpt(
        add_dxp_mcas(range_=[0, 1, 2, 3]),
        kind=Kind.normal | Kind.hinted,
        default_read_attrs=[f"mca{i}" for i in [0, 1, 2, 3]],
        default_configuration_attrs=[f"mca{i}" for i in [0, 1, 2, 3]],
    )


@pytest.fixture()
def dxp(sim_registry):
    FakeDXP = make_fake_device(DxpVortex)
    vortex = FakeDXP(name="vortex_me4", labels={"xrf_detectors", "detectors"})
    # vortex.net_cdf.dimensions.set([1477326, 1, 1])
    sim_registry.register(vortex)
    yield vortex


@pytest.fixture()
async def xspress(sim_registry):
    vortex = Xspress3Detector(name="vortex_me4", prefix="255id_vortex:", elements=4)
    await vortex.connect(mock=True)
    sim_registry.register(vortex)
    yield vortex


@pytest.fixture()
def robot(sim_registry):
    RobotClass = make_fake_device(Robot)
    robot = RobotClass(name="robotA", prefix="255idA:")
    sim_registry.register(robot)
    return robot


@pytest.fixture()
async def mono(sim_registry):
    mono = devices.AxilonMonochromator(name="monochromator", prefix="255idfNP:")
    await mono.connect(mock=True)
    sim_registry.register(mono)
    yield mono


@pytest.fixture()
async def undulator(sim_registry):
    undulator = devices.PlanarUndulator(
        name="undulator", prefix="ID255:DSID:", offset_pv="255idfNP:IDOffset"
    )
    await undulator.connect(mock=True)
    sim_registry.register(undulator)
    yield undulator


@pytest.fixture()
def aps(sim_registry):
    aps = instantiate_fake_device(ApsMachine, name="APS")
    sim_registry.register(aps)
    yield aps


@pytest.fixture()
async def xia_shutter_bank(sim_registry):
    bank = PFCUFilterBank(
        prefix="255id:pfcu4:", name="xia_filter_bank", shutters=[[2, 3]]
    )
    await bank.connect(mock=True)
    sim_registry.register(bank)
    yield bank


@pytest.fixture()
def xia_shutter(xia_shutter_bank):
    shutter = xia_shutter_bank.shutters[0]
    yield shutter


@pytest.fixture()
async def shutters(sim_registry):
    kw = dict(
        prefix="_prefix",
        labels={"shutters"},
        hutch_prefix="255ID:StaC:",
    )
    shutters = [
        PssShutter(name="Shutter A", **kw),
        PssShutter(name="Shutter C", **kw),
    ]
    [sim_registry.register(s) for s in shutters]
    yield shutters


@pytest.fixture()
async def filters(sim_registry):
    filters = [
        PFCUFilter(name="Filter A", prefix="filter1"),
        PFCUFilter(name="Filter B", prefix="filter2"),
    ]
    [sim_registry.register(f) for f in filters]
    await asyncio.gather(*(filter.connect(mock=True) for filter in filters))
    return filters


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
