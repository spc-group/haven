import logging

from apstools.devices.aps_machine import ApsMachineParametersDevice
from ophyd import Component as Cpt
from ophyd import EpicsSignalRO

log = logging.getLogger(__name__)


class ApsMachine(ApsMachineParametersDevice):
    _default_read_attrs = [
        "current",
        "lifetime",
    ]
    _default_configuration_attrs = [
        "aps_cycle",
        "machine_status",
        "operating_mode",
        "shutter_status",
        "fill_number",
        "orbit_correction",
        # Removed in apstools 1.6.20
        # "global_feedback",
        # "global_feedback_h",
        # "global_feedback_v",
        "operator_messages",
    ]
    shutter_status = Cpt(EpicsSignalRO, "RF-ACIS:FePermit:Sect1To35IdM.RVAL")

    def __init__(
        self,
        prefix: str = "",
        *,
        name: str,
        labels: set[str] = {"synchrotrons"},
        **kwargs,
    ):
        super().__init__(prefix=prefix, name=name, labels=labels, **kwargs)


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
