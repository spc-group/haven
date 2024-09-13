from firefly.slits import SlitsDisplay

# from haven.instrument import mirrors


class KBMirrorsDisplay(SlitsDisplay):

    def ui_filename(self):
        return "kb_mirrors.ui"

    def customize_ui(self):
        # Enable/disable bender controls
        horiz = self.device.horiz
        self.ui.horizontal_upstream_display.setEnabled(
            hasattr(horiz, "bender_upstream")
        )
        self.ui.horizontal_downstream_display.setEnabled(
            hasattr(horiz, "bender_downstream")
        )
        vert = self.device.vert
        self.ui.vertical_upstream_display.setEnabled(hasattr(vert, "bender_upstream"))
        self.ui.vertical_downstream_display.setEnabled(
            hasattr(vert, "bender_downstream")
        )


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
