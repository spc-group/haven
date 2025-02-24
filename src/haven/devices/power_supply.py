import logging

from ophyd import Device, EpicsSignal, EpicsSignalRO
from ophyd import FormattedComponent as FCpt

log = logging.getLogger(__name__)


class NHQ203MChannel(Device):
    """A single channel on a controllable power supply."""

    ch_num: int

    # Device components
    potential = FCpt(
        EpicsSignal,
        name="potential",
        suffix="{prefix}:Volt{ch_num}_rbv",
        write_pv="{prefix}:SetVolt{ch_num}",
        tolerance=2,
    )
    current = FCpt(EpicsSignalRO, name="current", suffix="{prefix}:Curr{ch_num}_rbv")
    ramp_rate = FCpt(
        EpicsSignal,
        name="ramp_rate",
        suffix="{prefix}:RampSpeed{ch_num}",
        write_pv="{prefix}:RampSpeed{ch_num}_rbv",
    )
    status = FCpt(EpicsSignalRO, name="status", suffix="{prefix}:ModStatus{ch_num}_rbv")

    def __init__(
        self,
        prefix: str,
        ch_num: int,
        name: str,
        labels={"power_supplies"},
        *args,
        **kwargs,
    ):
        self.ch_num = ch_num
        super().__init__(prefix=prefix, name=name, labels=labels, *args, **kwargs)


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
