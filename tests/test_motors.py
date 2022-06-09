import unittest

from haven import motors


class MonochromatorTests(unittest.TestCase):
    @unittest.expectedFailure
    def test_mono_exists(self):
        assert False, "Write the mono motor definition first."
