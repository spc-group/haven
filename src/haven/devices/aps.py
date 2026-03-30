import logging

from ophyd_async.core import (
    StandardReadable,
)
from ophyd_async.core import StandardReadableFormat as Format
from ophyd_async.core import (
    StrictEnum,
    SubsetEnum,
)
from ophyd_async.epics.core import epics_signal_r

log = logging.getLogger(__name__)


class ApsMachine(StandardReadable):

    _ophyd_labels_ = {"synchrotrons"}

    class MachineStatus(SubsetEnum):
        UNKNOWN = "State Unknown"
        USER_OPERATIONS = "USER OPERATIONS"
        SUPPLEMENTAL_TIME = "SUPLEMENTAL TIME"
        ASD_STUDIES = "ASD Studies"
        NO_BEAM = "NO BEAM"
        MAINTENANCE = "MAINTENANCE"

    class OperatingMode(StrictEnum):
        STATE_UNKNOWN = "State Unknown"
        NO_BEAM = "NO BEAM"
        INJECTING = "Injecting"
        STORED_BEAM = "Stored Beam"
        DELIVERED_BEAM = "Delivered Beam"
        MAINTENANCE = "MAINTENANCE"

    def __init__(self, prefix: str = "APS:", *, name: str = ""):
        with self.add_children_as_readables():
            self.current = epics_signal_r(float, "S-DCCT:CurrentM")
        with self.add_children_as_readables(Format.CONFIG_SIGNAL):
            self.operators = epics_signal_r(str, "OPS:message1")
            self.floor_coordinator = epics_signal_r(str, "OPS:message2")
            self.fill_pattern = epics_signal_r(str, "OPS:message3")
            self.last_problem_message = epics_signal_r(str, "OPS:message4")
            self.last_trip_message = epics_signal_r(str, "OPS:message5")
            # messages 6-8: meaning?
            self.message6 = epics_signal_r(str, "OPS:message6")
            self.message7 = epics_signal_r(str, "OPS:message7")
            self.message8 = epics_signal_r(str, "OPS:message8")
            self.machine_status = epics_signal_r(self.MachineStatus, "S:DesiredMode")
            self.operating_mode = epics_signal_r(self.OperatingMode, "S:ActualMode")
            self.shutter_status = epics_signal_r(bool, "XFD:ShutterPermit")
            self.shutters_open = epics_signal_r(int, "NoOfShuttersOpenA")
            self.fill_number = epics_signal_r(int, "S:FillNumber")
            self.orbit_correction = epics_signal_r(float, "S:OrbitCorrection:CC")
        super().__init__(name=name)


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
