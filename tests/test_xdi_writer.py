import pytest
from unittest import TestCase, expectedFailure
from io import StringIO
import os
import time
from pathlib import Path
import datetime as dt
import logging

# from freezegun import freeze_time
import pytz
import time_machine
from bluesky import RunEngine
from ophyd.sim import motor, SynGauss, SynAxis
import numpy as np
from numpy import asarray as array


from haven import XDIWriter, exceptions, energy_scan


fake_time = pytz.timezone("America/New_York").localize(
    dt.datetime(2022, 8, 19, 19, 10, 51)
)


log = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)


# Stub the epics signals in Haven

THIS_DIR = Path(__file__).parent


# Sample metadata dict
{
    "E0": 0,
    "beamline": {
        "is_connected": False,
        "name": "SPC Beamline (sector unknown)",
        "pv_prefix": "",
    },
    "detectors": ["I0", "It"],
    "edge": "Ni_K",
    "facility": {"name": "Advanced Photon Source", "xray_source": "insertion device"},
    "hints": {"dimensions": [(["energy", "exposure"], "primary")]},
    "ion_chambers": {"scaler": {"pv_prefix": ""}},
    "motors": ["energy", "exposure"],
    "num_intervals": 9,
    "num_points": 10,
    "plan_args": {
        "args": [
            "SynAxis(prefix='', name='energy', "
            "read_attrs=['readback', 'setpoint'], "
            "configuration_attrs=['velocity', 'acceleration'])",
            array([8300, 8310, 8320, 8330, 8340, 8350, 8360, 8370, 8380, 8390]),
            "SynAxis(prefix='', name='exposure', "
            "read_attrs=['readback', 'setpoint'], "
            "configuration_attrs=['velocity', 'acceleration'])",
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        ],
        "detectors": [
            "SynGauss(prefix='', name='I0', "
            "read_attrs=['val'], configuration_attrs=['Imax', "
            "'center', 'sigma', 'noise', 'noise_multiplier'])",
            "SynGauss(prefix='', name='It', "
            "read_attrs=['val'], configuration_attrs=['Imax', "
            "'center', 'sigma', 'noise', "
            "'noise_multiplier'])",
        ],
        "per_step": "None",
    },
    "plan_name": "list_scan",
    "plan_pattern": "inner_list_product",
    "plan_pattern_args": {
        "args": [
            "SynAxis(prefix='', name='energy', "
            "read_attrs=['readback', 'setpoint'], "
            "configuration_attrs=['velocity', "
            "'acceleration'])",
            array([8300, 8310, 8320, 8330, 8340, 8350, 8360, 8370, 8380, 8390]),
            "SynAxis(prefix='', name='exposure', "
            "read_attrs=['readback', 'setpoint'], "
            "configuration_attrs=['velocity', "
            "'acceleration'])",
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        ]
    },
    "plan_pattern_module": "bluesky.plan_patterns",
    "plan_type": "generator",
    "sample_name": "NiO_rock_salt",
    "scan_id": 1,
    "time": 1661025010.409619,
    "uid": "671c3c48-f014-421d-b3e0-57991b6745f6",
    "versions": {"bluesky": "1.8.3", "ophyd": "1.6.4"},
}


@pytest.fixture()
def stringio():
    yield StringIO()


class CallbackTests(TestCase):
    stringio = None
    file_path = THIS_DIR / "sample_file.txt"
    start_doc = {
        "versions": {"bluesky": "1.8.3", "ophyd": "1.6.4"},
        "detectors": ["I0", "It"],
        "motors": ["energy", "exposure"],
        "edge": "Ni_K",
        "facility": {
            "name": "Advanced Photon Source",
            "xray_source": "insertion device",
        },
        "beamline": {"name": "20-ID-C", "pv_prefix": "20id:"},
        "sample_name": "nickel oxide",
        "uid": "671c3c48-f014-421d-b3e0-57991b6745f6",
    }
    event_doc = {
        "data": {"I0": 2, "It": 1.5, "energy": 8330, "exposure": 0.1},
        "time": 1660186828.0055554,
    }

    def setUp(self):
        self.stringio = StringIO()

    def tearDown(self):
        for fp in [
            self.file_path,
            Path("{year}{month}{day}_{sample_name}.xdi"),
            Path("20220819_nickel-oxide.xdi"),
        ]:
            if fp.exists():
                fp.unlink()

    def test_opens_file(self):
        # Pass in a string and it should hold the path until the start document is found
        writer = XDIWriter(self.file_path)
        self.assertEqual(writer.fp, self.file_path)
        self.assertFalse(self.file_path.exists())
        # Run the writer
        writer("start", {"edge": "Ni_K"})
        # Check that a file was created
        self.assertTrue(self.file_path.exists())

    def test_uses_open_file(self):
        # Pass in a string and it should hold the path until the start document is found
        writer = XDIWriter(self.stringio)
        self.assertIs(writer.fd, self.stringio)

    def test_read_only_file(self):
        # Check that it raises an exception if an open file has no write intent
        # Put some content in the temporary file
        with open(self.file_path, mode="w") as fd:
            fd.write("Hello, spam!")
        # Check that the writer raises an exception when the file is open read-only
        with open(self.file_path, mode="r") as fd:
            with self.assertRaises(exceptions.FileNotWritable):
                XDIWriter(fd)

    @expectedFailure
    def test_required_headers(self):
        writer = XDIWriter(self.stringio)
        writer("start", self.start_doc)
        # Check that required headers were added to the XDI file
        self.stringio.seek(0)
        xdi_output = self.stringio.read()
        self.assertIn("# XDI/1.0 bluesky/1.8.3 ophyd/1.6.4", xdi_output)
        self.assertIn("# Column.1: energy", xdi_output)
        self.assertIn("# Element.symbol: Ni", xdi_output)
        self.assertIn("# Element.edge: K", xdi_output)
        self.assertIn("# Mono.d_spacing: 3", xdi_output)
        self.assertIn("# -------------")

    @time_machine.travel(fake_time)
    def test_optional_headers(self):
        writer = XDIWriter(self.stringio)
        os.environ["TZ"] = "America/New_York"
        time.tzset()
        writer("start", self.start_doc)
        writer("event", self.event_doc)
        # Check that required headers were added to the XDI file
        self.stringio.seek(0)
        xdi_output = self.stringio.read()
        expected_metadata = {
            "Facility.name": "Advanced Photon Source",
            "Facility.xray_source": "insertion device",
            "Beamline.name": "20-ID-C",
            "Beamline.pv_prefix": "20id:",
            "Scan.start_time": "2022-08-19 19:10:51-0400",
            "Column.5": "time",
            "uid": "671c3c48-f014-421d-b3e0-57991b6745f6",
        }
        for key, val in expected_metadata.items():
            self.assertIn(f"# {key.lower()}: {val.lower()}\n", xdi_output.lower())

    @time_machine.travel(fake_time)
    def test_file_path_formatting(self):
        """Check that "{date}_{user}.xdi" formatting works in the filename."""
        writer = XDIWriter("{year}{month}{day}_{sample_name}.xdi")
        writer.start(self.start_doc)
        self.assertEqual(str(writer.fp), "20220819_nickel-oxide.xdi")

    def test_file_path_formatting_bad_key(self):
        """Check that "{date}_{user}.xdi" raises exception if placeholder is invalid."""
        writer = XDIWriter("{year}{month}{day}_{spam}_{sample_name}.xdi")
        with self.assertRaises(exceptions.XDIFilenameKeyNotFound):
            writer.start(self.start_doc)

    def test_data(self):
        """Check that the TSV data section is present and correct."""
        writer = XDIWriter(self.stringio)
        writer.start(self.start_doc)
        writer("event", self.event_doc)
        # Verify the data were written properly
        self.stringio.seek(0)
        xdi_output = self.stringio.read()
        self.assertIn("8330", xdi_output)
        self.assertIn("1660186828.0055554", xdi_output)


def test_with_plan(stringio, sim_registry):
    I0 = SynGauss(
        "I0",
        motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"detectors"},
    )
    It = SynGauss(
        "It",
        motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"detectors"},
    )
    energy_motor = SynAxis(name="energy", labels={"motors", "energies"})
    exposure = SynAxis(name="exposure", labels={"motors", "exposures"})
    writer = XDIWriter(stringio)
    RE = RunEngine()
    energy_plan = energy_scan(
        np.arange(8300.0, 8400.0, 10),
        detectors=[I0, It],
        E0="Ni_K",
        energy_positioners=[energy_motor],
        time_positioners=[exposure],
        md=dict(sample_name="NiO_rock_salt"),
    )
    RE(energy_plan, writer)
