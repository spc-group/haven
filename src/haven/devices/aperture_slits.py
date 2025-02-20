"""This is a copy of the apstools Slits support with signals for the tweak PV."""

import logging

from ophyd_async.core import StandardReadable

from .motor import Motor

__all__ = ["ApertureSlits", "SlitAxis"]

log = logging.getLogger(__name__)


# Make *readback* and *setpoint* available to match other slits
class SlitMotor(Motor):
    @property
    def readback(self):
        return self.user_readback

    @property
    def setpoint(self):
        return self.user_setpoint


class SlitAxis(StandardReadable):
    def __init__(self, prefix: str, name: str = ""):
        with self.add_children_as_readables():
            self.size = SlitMotor(f"{prefix}Size")
            self.center = SlitMotor(f"{prefix}Center")
        super().__init__(name=name)


class ApertureSlits(StandardReadable):
    """A rotating aperture that functions like a set of slits.

    Unlike the blade slits, there are no independent parts to move,
    so each axis only has center and size.

    Based on the 25-ID-A whitebeam slits.

    """

    _ophyd_labels_ = {"slits"}

    def __init__(
        self,
        prefix: str,
        name: str = "",
    ):
        # Individual slit directions
        with self.add_children_as_readables():
            self.horizontal = SlitAxis(f"{prefix}h")
            self.vertical = SlitAxis(f"{prefix}v")
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
