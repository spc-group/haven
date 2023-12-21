from ophyd import DetectorBase

from haven import load_config, registry
from haven.instrument.camera import AravisDetector, load_cameras

PREFIX = "255idgigeA:"


def test_load_cameras():
    load_cameras(config=load_config())
    # Check that cameras were registered
    cameras = list(registry.findall(label="cameras"))
    assert len(cameras) == 1
    assert isinstance(cameras[0], DetectorBase)


def test_camera_device():
    camera = AravisDetector(PREFIX, name="camera")
    assert isinstance(camera, DetectorBase)
    assert hasattr(camera, "cam")


def test_camera_in_registry(sim_registry):
    camera = AravisDetector(PREFIX, name="camera")
    sim_registry.register(camera)
    # Check that all sub-components are accessible
    camera = sim_registry.find(camera.name)
    cam = sim_registry.find(f"{camera.name}_cam")
    gain = sim_registry.find(f"{camera.name}_cam.gain")


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
