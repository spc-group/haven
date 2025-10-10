"""
ApsMachineParameters fails to create with KeyError.

BUGFIX for new fiscal year: 2025-10-01

For BITS users:

1. Install this patch file in your instrument's `devices/` directory with name
   `patched_aps.py`.
2. In your `devices.yml` (or equal), replace
   `apstools.devices.ApsMachineParametersDevice` with
   `INSTRUMENT.devices.patched_aps.PatchedApsMachineParametersDevice`
   where `INSTRUMENT` is the name of your specific instrument package.

For others:

1. same as step 1 above
2. create your `aps` object with this code:

   from INSTRUMENT.devices.patched_aps import PatchedApsMachineParametersDevice
   aps = PatchedApsMachineParametersDevice("", name="aps")
"""

from apstools.devices import ApsMachineParametersDevice
from apstools.devices.aps_cycle import ApsCycleDM
from ophyd import Component


class PatchedApsCycleDM(ApsCycleDM):
    """BUGFIX for new fiscal year."""

    _cycle_ends = "2025-12-31 23:59:59"  # TODO: official date in 2026-01
    _cycle_name = "2025-3"  # TODO: apstools needs update

    def get(self):
        return self._cycle_name


class PatchedApsMachineParametersDevice(ApsMachineParametersDevice):
    """BUGFIX for new fiscal year."""

    aps_cycle = Component(PatchedApsCycleDM)
