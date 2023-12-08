from haven import registry
from haven.instrument import shutter


def test_shutter(sim_registry, beamline_connected):
    shutter.load_shutters()
    shutters = list(registry.findall(label="shutters"))
    assert len(shutters) == 2
    shutterA = registry.find(name="front_end_shutter")
    assert shutterA.name == "front_end_shutter"
    assert shutterA.open_signal.pvname == "PSS:99ID:FES_OPEN_EPICS.VAL"
    assert shutterA.close_signal.pvname == "PSS:99ID:FES_CLOSE_EPICS.VAL"
    assert shutterA.pss_state.pvname == "PSS:99ID:A_BEAM_PRESENT"
    shutterC = registry.find(name="hutch_shutter")
    assert shutterC.name == "hutch_shutter"
    assert shutterC.open_signal.pvname == "PSS:99ID:SCS_OPEN_EPICS.VAL"
    assert shutterC.close_signal.pvname == "PSS:99ID:SCS_CLOSE_EPICS.VAL"
    assert shutterC.pss_state.pvname == "PSS:99ID:C_BEAM_PRESENT"


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
