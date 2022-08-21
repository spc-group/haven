import unittest
import logging
from pathlib import Path

from haven._iconfig import load_config


class IconfigTests(unittest.TestCase):
    def test_default_values(self):
        config = load_config()
        self.assertIn("beamline", config.keys())

    def test_loading_a_file(self):
        test_file = Path(__file__).resolve().parent / "test_iconfig.toml"
        config = load_config(file_paths=[test_file])
        self.assertEqual(config["beamline"]["pv_prefix"], "spam")
