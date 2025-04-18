import numpy as np
import pytest
from bluesky import RunEngine
from ophyd import sim
from ophyd_async.sim._sim_motor import SimMotor

from haven.devices import EnergyPositioner
from haven.energy_ranges import ERange, KRange, from_tuple
from haven.plans import energy_scan, xafs_scan


@pytest.fixture()
async def energy_positioner():
    device = EnergyPositioner(
        name="energy", monochromator_prefix="255idMono:", undulator_prefix="255ID:DS:"
    )
    await device.connect(mock=True)
    return device


@pytest.fixture()
def mono_motor():
    return sim.SynAxis(name="mono_energy", labels={"motors", "energies"})


@pytest.fixture()
def id_gap_motor():
    return sim.SynAxis(name="id_gap_energy", labels={"motors", "energies"})


@pytest.fixture()
def exposure_motor():
    return sim.Signal(name="exposure")


@pytest.fixture()
def energies():
    return np.linspace(8300, 8500, 100)


@pytest.fixture()
def I0(sim_registry):
    # Register an ion chamber
    I0 = sim.SynGauss(
        "I0",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"ion_chambers"},
    )
    sim_registry.register(I0)
    return I0


def test_energy_scan_basics(
    beamline_manager, mono_motor, id_gap_motor, energies, RE, tmp_path
):
    beamline_manager.local_storage.full_path._readback = str(tmp_path)
    exposure_time = 1e-3
    # Set up fake detectors and motors
    I0_exposure = sim.SynAxis(
        name="I0_exposure",
        labels={
            "exposures",
        },
    )
    It_exposure = sim.SynAxis(
        name="It_exposure",
        labels={
            "exposures",
        },
    )
    I0 = sim.SynGauss(
        name="I0",
        motor=mono_motor,
        motor_field="mono_energy",
        center=np.median(energies),
        Imax=1,
        sigma=1,
        labels={"detectors"},
    )
    It = sim.SynSignal(
        func=lambda: 1.0,
        name="It",
        exposure_time=exposure_time,
    )
    # Execute the plan
    scan = energy_scan(
        energies,
        detectors=[I0, It],
        exposure=exposure_time,
        energy_signals=[mono_motor, id_gap_motor],
        time_signals=[I0_exposure, It_exposure],
        md={"edge": "Ni_K"},
    )
    result = RE(scan, sample_name="xafs_sample")
    # Check that the mono and ID gap ended up in the right position
    # time.sleep(1.0)
    assert mono_motor.readback.get() == np.max(energies)
    # assert mono_motor.get().readback == np.max(energies)
    assert id_gap_motor.get().readback == np.max(energies)
    assert I0_exposure.get().readback == exposure_time
    assert It_exposure.get().readback == exposure_time


def test_raises_on_empty_positioners(RE, energies):
    with pytest.raises(ValueError):
        RE(energy_scan(energies, energy_signals=[]))


def test_single_range(mono_motor, exposure_motor, I0):
    E0 = 10000
    expected_energies = np.arange(9990, 10001, step=1)
    expected_exposures = np.asarray([1.0])
    scan = xafs_scan(
        [],
        # (start, stop, step, time)
        (-10, 0, 1, 1),
        E0=E0,
        energy_signals=[mono_motor],
        time_signals=[exposure_motor],
    )
    # Check that the mono motor is moved to the correct positions
    scan_list = list(scan)
    real_energies = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "mono_energy"
    ]
    np.testing.assert_equal(real_energies, expected_energies)
    # Check that the exposure is set correctly
    real_exposures = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "exposure"
    ]
    np.testing.assert_equal(real_exposures, expected_exposures)


def test_multi_range(mono_motor, exposure_motor, I0):
    E0 = 10000
    expected_energies = np.concatenate(
        [
            np.arange(9990, 10001, step=2),
            np.arange(10001, 10011, step=1),
        ]
    )
    expected_exposures = np.asarray([0.5, 1.0])
    scan = xafs_scan(
        [],
        ERange(-10, 0, 2, 0.5),
        ERange(0, 10, 1, 1.0),
        E0=E0,
        energy_signals=[mono_motor],
        time_signals=[exposure_motor],
    )
    # Check that the mono motor is moved to the correct positions
    scan_list = list(scan)
    real_energies = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "mono_energy"
    ]
    np.testing.assert_equal(real_energies, expected_energies)
    # Check that the exposure is set correctly
    real_exposures = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "exposure"
    ]
    np.testing.assert_equal(real_exposures, expected_exposures)


def test_exafs_k_range(mono_motor, exposure_motor, I0):
    """Ensure that passing in k_min, etc. produces an energy range
    in K-space.

    """
    E0 = 10000
    E_min = 10
    k_min = 1.6200877248145786
    krange = KRange(k_min, 14, step=0.5, weight=0.5, exposure=0.75)
    expected_energies = krange.energies() + E0
    expected_exposures = krange.exposures()
    scan = xafs_scan(
        [],
        KRange(k_min, 14, step=0.5, exposure=0.75, weight=0.5),
        E0=E0,
        energy_signals=[mono_motor],
        time_signals=[exposure_motor],
    )
    # Check that the mono motor is moved to the correct positions
    scan_list = list(scan)
    real_energies = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "mono_energy"
    ]
    np.testing.assert_almost_equal(real_energies, expected_energies)
    # Check that the exposure is set correctly
    real_exposures = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "exposure"
    ]
    np.testing.assert_almost_equal(real_exposures, expected_exposures)


def test_named_E0(mono_motor, exposure_motor, I0):
    expected_energies = np.concatenate(
        [
            np.arange(8323, 8334, step=2),
            np.arange(8334, 8344, step=1),
        ]
    )
    expected_exposures = np.asarray([0.5, 1.0])
    scan = xafs_scan(
        [],
        ERange(-10, 0, 2, exposure=0.5),
        ERange(0, 10, 1, exposure=1.0),
        E0="Ni_K",
        energy_signals=[mono_motor],
        time_signals=[exposure_motor],
    )
    # Check that the mono motor is moved to the correct positions
    scan_list = list(scan)
    real_energies = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "mono_energy"
    ]
    np.testing.assert_equal(real_energies, expected_energies)
    # Check that the exposure is set correctly
    real_exposures = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj.name == "exposure"
    ]
    np.testing.assert_equal(real_exposures, expected_exposures)


def test_uses_default_time_signals(dxp, mono_motor):
    """Test that the default time positioners are used if no specific ones are given."""
    scan = xafs_scan(
        [dxp],
        ERange(-10, 0, 2, exposure=0.5),
        E0=0,
        time_signals=None,
        energy_signals=[mono_motor],
    )
    msgs = list(scan)
    set_msgs = [m for m in msgs if m.command == "set" and dxp.name in m.obj.name]
    assert len(set_msgs) == 1
    time_msg = set_msgs[0]
    assert time_msg.obj is dxp.preset_real_time
    assert time_msg.args[0] == 0.5


def test_remove_duplicate_energies(mono_motor, exposure_motor, I0):
    plan = xafs_scan(
        "ion_chambers",
        ERange(-4, 6, 2),
        ERange(6, 40, 34),
        E0=8333,
        energy_signals=[mono_motor],
        time_signals=[exposure_motor],
    )
    msgs = list(plan)
    set_msgs = [m for m in msgs if m.command == "set" and m.obj.name == "mono_energy"]
    read_msgs = [m for m in msgs if m.command == "read" and m.obj.name == "I0"]
    energies = [m.args[0] for m in set_msgs]
    # Make sure we only read each point once
    assert len(read_msgs) == len(energies)


def test_energy_scan_metadata(energy_positioner):
    scan = energy_scan(
        [],
        detectors=[],
        energy_signals=[energy_positioner],
        E0="Ni-K",
        md={"sample_name": "unobtanium"},
    )
    # First we need to inject an energy d_spacing reading
    msgs = []
    read_msg = None
    while read_msg is None:
        msgs.append(next(scan))
        if msgs[-1].command == "read":
            read_msg = msgs[-1]
    msgs.append(
        scan.send(
            {
                "energy-monochromator-d_spacing": {
                    "value": 3.134734,
                    "timestamp": 1742397744.329849,
                    "alarm_severity": 0,
                }
            }
        )
    )
    # Produce the rest of the msgs
    msgs.extend(list(scan))
    open_msg = [m for m in msgs if m.command == "open_run"][0]
    md = open_msg.kwargs
    # Check that the metadata has the right values
    assert md["edge"] == "Ni-K"
    assert md["E0"] == 8333.0
    assert md["d_spacing"] == 3.134734
    assert md["plan_name"] == "energy_scan"
    assert md["sample_name"] == "unobtanium"


async def test_energy_scan_metadata_multiple_monos(energy_positioner):
    """Having additional monochromators in the scan means we can have
    multiple sets of metadata.

    """
    mono2 = EnergyPositioner(monochromator_prefix="", undulator_prefix="", name="mono2")
    await mono2.connect(mock=True)
    scan = energy_scan(
        [1.0, 2.0, 3.0],
        detectors=[],
        energy_signals=[energy_positioner, mono2],
        E0="Ni-K",
        md={"sample_name": "unobtanium"},
    )
    # First we need to inject an energy d_spacing reading
    msgs = []
    read_msg = None
    while read_msg is None:
        msgs.append(next(scan))
        if msgs[-1].command == "read":
            read_msg = msgs[-1]
    msgs.extend(
        [
            scan.send(
                {
                    "energy-monochromator-d_spacing": {
                        "value": 3.134734,
                        "timestamp": 1742397744.329849,
                        "alarm_severity": 0,
                    }
                }
            ),
            scan.send(
                {
                    "mono2-monochromator-d_spacing": {
                        "value": 4.20,
                        "timestamp": 1742397744.329849,
                        "alarm_severity": 0,
                    }
                }
            ),
        ]
    )
    # Produce the rest of the msgs
    msgs.extend(list(scan))
    open_msg = [m for m in msgs if m.command == "open_run"][0]
    md = open_msg.kwargs
    # Check that the metadata has the right values
    assert md["edge"] == "Ni-K"
    assert md["E0"] == 8333.0
    assert md["d_spacing"] == [3.134734, 4.20]
    assert md["plan_name"] == "energy_scan"
    assert md["sample_name"] == "unobtanium"


def test_xafs_scan_metadata(mono_motor):
    scan = xafs_scan(
        [],
        ERange(0, 10),
        energy_signals=[mono_motor],
        E0="Ni-K",
        md={"sample_name": "unobtanium"},
    )
    # Get the metadata passed alongside the "open_run" message
    msgs = list(scan)
    open_msg = [m for m in msgs if m.command == "open_run"][0]
    md = open_msg.kwargs
    # Check that the metadata has the right values
    assert md["edge"] == "Ni-K"
    assert md["E0"] == 8333.0
    assert md["plan_name"] == "xafs_scan"
    assert md["sample_name"] == "unobtanium"
    assert md["plan_args"] == {
        "detectors": [],
        "energy_ranges": ["ERange(start=0, stop=10, step=1.0, exposure=0.5)"],
        "energy_signals": [
            (
                "SynAxis(prefix='', name='mono_energy', read_attrs=['readback', "
                "'setpoint'], configuration_attrs=['velocity', 'acceleration'])"
            )
        ],
        "time_signals": None,
        "E0": "Ni-K",
    }


async def test_document_plan_args():
    """Having numpy arrays in the arguments to a plan causes problems for
    the TiledWriter. Make sure that the start doc plan args do not
    contain numpy arrays.

    """
    # Set up mocked devices
    energy = SimMotor(name="energy")
    await energy.connect(mock=False)
    # Set up the run engine environment
    await energy.connect(mock=True)
    RE = RunEngine({})
    documents = []

    def track_doc(name, doc):
        documents.append((name, doc))

    RE.subscribe(track_doc)
    # Prepare the plan
    energies = np.linspace(8250, 8550, num=11)
    plan = energy_scan(energies=energies, detectors=[], energy_signals=[energy])
    RE(plan)
    (start_doc,) = [doc for name, doc in documents if name == "start"]
    # Make sure there are no numpy arrays in the plan args
    # (causes problems for the Tiled writer)
    args = start_doc["plan_args"]["args"]
    assert not any([isinstance(arg, np.ndarray) for arg in args])


def test_from_tuple():
    assert from_tuple(ERange(3, 9, 0.5)) == ERange(start=3, stop=9, step=0.5)
    assert from_tuple(("E", 10, 15)) == ERange(10, 15)
    assert from_tuple(("K", 4, 12, 0.1, 1.0, 1)) == KRange(
        start=4, stop=12, step=0.1, exposure=1.0, weight=1
    )
    assert from_tuple((10, 15, 0.25, 1.5)) == ERange(
        start=10, stop=15, step=0.25, exposure=1.5
    )


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
