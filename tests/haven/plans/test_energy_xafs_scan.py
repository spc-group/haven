import numpy as np
import pytest
from bluesky import RunEngine
from ophyd_async.testing import set_mock_value

from haven.devices import AxilonMonochromator as Monochromator
from haven.devices import PlanarUndulator
from haven.energy_ranges import ERange, KRange, from_tuple
from haven.plans._energy_scan import energy_scan
from haven.plans._xafs_scan import xafs_scan


@pytest.fixture()
async def mono():
    device = Monochromator("255idFUP:", name="mono")
    await device.connect(mock=True)
    return device


@pytest.fixture()
async def undulator():
    device = PlanarUndulator(
        "ID255:DSID:", name="undulator", offset_pv="255idbFP:id_offset"
    )
    await device.connect(mock=True)
    return device


@pytest.fixture()
def energies():
    return np.linspace(8300, 8500, 3)


def test_energy_scan_basics(mono, undulator, ion_chamber, energies, tmp_path):
    exposure_time = 1e-3
    # Execute the plan
    plan = energy_scan(
        energies,
        detectors=[ion_chamber],
        exposure=exposure_time,
        energy_devices=[mono, undulator],
        time_signals=[ion_chamber.default_time_signal],
        md={"edge": "Ni_K"},
    )
    msgs = list(plan)
    # Check that the mono and ID gap ended up in the right position
    set_msgs = [msg for msg in msgs if msg.command == "set"]
    mono_msgs = [msg for msg in set_msgs if msg.obj is mono.energy]
    mono_setpoints = [msg.args[0] for msg in mono_msgs]
    assert np.all(mono_setpoints == energies)
    id_msgs = [msg for msg in set_msgs if msg.obj is undulator.energy]
    id_setpoints = [msg.args[0] for msg in id_msgs]
    assert np.all(id_setpoints == energies)
    time_msgs = [msg for msg in set_msgs if msg.obj is ion_chamber.default_time_signal]
    time_setpoints = [msg.args[0] for msg in time_msgs]
    assert np.all(time_setpoints == [0.001])


def test_raises_on_empty_positioners(energies):
    with pytest.raises(ValueError):
        list(energy_scan(energies, energy_devices=[]))


def test_single_range(mono, ion_chamber):
    E0 = 10000
    expected_energies = np.arange(9990, 10001, step=1)
    expected_exposures = np.asarray([1.0])
    plan = xafs_scan(
        [],
        # (start, stop, step, time)
        (-10, 0, 1, 1),
        E0=E0,
        energy_devices=[mono],
        time_signals=[ion_chamber.default_time_signal],
    )
    # Check that the mono motor is moved to the correct positions
    scan_list = list(plan)
    real_energies = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj is mono.energy
    ]
    np.testing.assert_equal(real_energies, expected_energies)
    # Check that the exposure is set correctly
    real_exposures = [
        i.args[0]
        for i in scan_list
        if i[0] == "set" and i.obj is ion_chamber.default_time_signal
    ]
    np.testing.assert_equal(real_exposures, expected_exposures)


def test_multi_range(mono, ion_chamber):
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
        energy_devices=[mono],
        time_signals=[ion_chamber.default_time_signal],
    )
    # Check that the mono motor is moved to the correct positions
    scan_list = list(scan)
    real_energies = [
        i.args[0] for i in scan_list if i.command == "set" and i.obj is mono.energy
    ]
    np.testing.assert_equal(real_energies, expected_energies)
    # Check that the exposure is set correctly
    real_exposures = [
        i.args[0]
        for i in scan_list
        if i[0] == "set" and i.obj is ion_chamber.default_time_signal
    ]
    np.testing.assert_equal(real_exposures, expected_exposures)


def test_exafs_k_range(mono, ion_chamber):
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
        energy_devices=[mono],
        time_signals=[ion_chamber.default_time_signal],
    )
    # Check that the mono motor is moved to the correct positions
    scan_list = list(scan)
    real_energies = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj is mono.energy
    ]
    np.testing.assert_almost_equal(real_energies, expected_energies)
    # Check that the exposure is set correctly
    real_exposures = [
        i.args[0]
        for i in scan_list
        if i[0] == "set" and i.obj is ion_chamber.default_time_signal
    ]
    np.testing.assert_almost_equal(real_exposures, expected_exposures)


def test_named_E0(mono, ion_chamber):
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
        energy_devices=[mono],
        time_signals=[ion_chamber.default_time_signal],
    )
    # Check that the mono motor is moved to the correct positions
    scan_list = list(scan)
    real_energies = [
        i.args[0] for i in scan_list if i[0] == "set" and i.obj is mono.energy
    ]
    np.testing.assert_equal(real_energies, expected_energies)
    # Check that the exposure is set correctly
    real_exposures = [
        i.args[0]
        for i in scan_list
        if i[0] == "set" and i.obj is ion_chamber.default_time_signal
    ]
    np.testing.assert_equal(real_exposures, expected_exposures)


def test_uses_default_time_signals(xspress, mono):
    """Test that the default time positioners are used if no specific ones are given."""
    scan = xafs_scan(
        [xspress],
        ERange(-10, 0, 2, exposure=0.5),
        E0=0,
        time_signals=None,
        energy_devices=[mono],
    )
    msgs = list(scan)
    set_msgs = [
        m for m in msgs if m.command == "set" and m.obj is xspress.driver.acquire_time
    ]
    assert len(set_msgs) == 1
    time_msg = set_msgs[0]
    assert time_msg.obj is xspress.driver.acquire_time
    assert time_msg.args[0] == 0.5


def test_remove_duplicate_energies(mono, ion_chamber):
    plan = xafs_scan(
        "ion_chambers",
        ERange(-4, 6, 2),
        ERange(6, 40, 34),
        E0=8333,
        energy_devices=[mono],
        time_signals=[ion_chamber.default_time_signal],
    )
    msgs = list(plan)
    set_msgs = [m for m in msgs if m.command == "set" and m.obj is mono.energy]
    read_msgs = [m for m in msgs if m.command == "read" and m.obj is ion_chamber]
    energies = [m.args[0] for m in set_msgs]
    # Make sure we only read each point once
    assert len(read_msgs) == len(energies)


def test_energy_scan_metadata(mono):
    scan = energy_scan(
        [],
        detectors=[],
        energy_devices=[mono],
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
                f"{mono.name}-d_spacing": {
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


async def test_energy_scan_metadata_multiple_monos(mono):
    """Having additional monochromators in the scan means we can have
    multiple sets of metadata.

    """
    mono2 = Monochromator(prefix="", name="mono2")
    await mono2.connect(mock=True)
    scan = energy_scan(
        [1.0, 2.0, 3.0],
        detectors=[],
        energy_devices=[mono, mono2],
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
    readings = {
        f"{mono.name}-d_spacing": {
            "value": 3.134734,
            "timestamp": 1742397744.329849,
            "alarm_severity": 0,
        },
        f"{mono2.name}-d_spacing": {
            "value": 4.20,
            "timestamp": 1742397744.329849,
            "alarm_severity": 0,
        },
    }
    msgs.extend(
        [
            scan.send(readings),
            scan.send(readings),
        ]
    )
    # Produce the rest of the msgs
    msgs.extend(list(scan))
    open_msg = [m for m in msgs if m.command == "open_run"][0]
    md = open_msg.kwargs
    # Check that the metadata has the right values
    assert md["edge"] == "Ni-K"
    assert md["E0"] == 8333.0
    assert md["d_spacing"] == {"mono2-d_spacing": 4.20, "mono-d_spacing": 3.134734}
    assert md["plan_name"] == "energy_scan"
    assert md["sample_name"] == "unobtanium"


def test_xafs_scan_metadata(mono):
    scan = xafs_scan(
        [],
        ERange(0, 10),
        energy_devices=[mono],
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
        "energy_devices": [repr(mono)],
        "time_signals": None,
        "E0": "Ni-K",
    }


async def test_document_plan_args(mono):
    """Having numpy arrays in the arguments to a plan causes problems for
    the TiledWriter. Make sure that the start doc plan args do not
    contain numpy arrays.

    """
    # Set up the run engine environment
    RE = RunEngine({})
    documents = []

    def track_doc(name, doc):
        documents.append((name, doc))

    RE.subscribe(track_doc)
    set_mock_value(mono.energy.velocity, 1)
    # Prepare the plan
    energies = np.linspace(8250, 8550, num=11)
    await mono.energy.high_limit_travel.set(10_000)
    plan = energy_scan(energies=energies, detectors=[], energy_devices=[mono])
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
