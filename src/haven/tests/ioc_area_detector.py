#!/usr/bin/env python3
from caproto.server import (
    PVGroup,
    PvpropertyInteger,
    SubGroup,
    ioc_arg_parser,
    pvproperty,
    run,
)


class AreaDetectorGroup(PVGroup):
    """An IOC matching an EPICS area detector.

    Currently does not describe a full area detector setup. It is just
    meant to provide the bare essentials.

    """

    class CameraGroup(PVGroup):
        acquire_rbv = pvproperty(value=0, name="Acquire_RBV", dtype=PvpropertyInteger)
        acquire = pvproperty(value=0, name="Acquire", dtype=PvpropertyInteger)
        acquire_busy = pvproperty(value=0, name="AcquireBusy", dtype=PvpropertyInteger)
        gain = pvproperty(value=10, name="Gain")
        gain_rbv = pvproperty(value=10, name="Gain_RBV")

    cam = SubGroup(CameraGroup, prefix="cam1:")


if __name__ == "__main__":
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="255idSimDet:", desc="haven.tests.ioc_area_detector test IOC"
    )
    ioc = AreaDetectorGroup(**ioc_options)
    run(ioc.pvdb, **run_options)


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
