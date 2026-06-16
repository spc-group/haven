import math

from qtpy import QtWidgets

HALF_SPACE = "\u202f"


class DurationLabel(QtWidgets.QLabel):
    """A label that shows individual hours, minutes, seconds, etc."""

    def set_seconds(self, seconds: float | int, efficiency: float | None = None):
        """Set the duraction, in seconds.

        Will update the text to show the new duration. If *efficiency*
        is provided, the number will be shown as a per cent (i.e. how
        much of the time is spent collecting data vs moving motors).

        """
        if math.isnan(seconds):
            text = f"–{HALF_SPACE}h –{HALF_SPACE}m –{HALF_SPACE}s"
        else:
            hours, more_seconds = divmod(seconds, 3600)
            minutes, more_seconds = divmod(more_seconds, 60)
            text = f"{int(hours)}{HALF_SPACE}h {int(minutes)}{HALF_SPACE}m {math.ceil(more_seconds)}{HALF_SPACE}s"
            if efficiency is not None and math.isfinite(efficiency):
                text += f" ({int(efficiency*100)}{HALF_SPACE}%)"
        self.setText(text)


# -----------------------------------------------------------------------------
# :author:    Juanjuan Huang, Mark Wolfman
# :email:     juanjuan.huang@anl.gov, wolfman@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
