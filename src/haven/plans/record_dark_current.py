from bluesky import plan_stubs as bps

from ..instrument.instrument_registry import registry
from .shutters import close_shutters, open_shutters


def record_dark_current(ion_chambers, shutters, time):
    """Record the dark current on the ion chambers.

    - Close shutters
    - Record ion chamber dark current
    - Open shutters

    Parameters
    ==========
    ion_chambers
      Ion chamber devices or names.
    shutters
      Shutter devices or names.

    """
    yield from close_shutters(shutters)
    # Measure the dark current
    ion_chambers = registry.findall(ion_chambers)
    # This is a big hack, we need to come back and just accept the current integration time
    old_times = [ic.exposure_time.get() for ic in ion_chambers]
    time_args = [obj for ic in ion_chambers for obj in (ic.record_dark_time, time)]
    yield from bps.mv(*time_args)
    mv_args = [obj for ic in ion_chambers for obj in (ic.record_dark_current, 1)]
    triggers = [ic.record_dark_current for ic in ion_chambers]
    yield from bps.mv(*mv_args)
    yield from bps.sleep(time)
    time_args = [
        obj for (ic, t) in zip(ion_chambers, old_times) for obj in (ic.exposure_time, t)
    ]
    yield from bps.mv(*time_args)
    # Open shutters again
    yield from open_shutters(shutters)


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
