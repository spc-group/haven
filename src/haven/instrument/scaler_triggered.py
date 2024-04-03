from ophyd import EpicsSignal, EpicsSignalRO

__all__ = ["ScalerTriggered"]


class ScalerTriggered:
    """A mix-in for triggering a device using the scaler.

    The device does not have to be a channel on the scaler, enabling
    hardware triggering of other devices.

    If this is a used as part of a component, then triggering is left
    up to the parent device.

    If this is used as part of a top-level Device, then the device
    should have a *scaler_prefix* attribute with the PV prefix to the
    scaler (e.g. "25idcVME:scaler1"), though this is only used to
    coordinate statuses for multiple devices using the same scaler.

    """

    scaler_prefix = None
    _statuses = {}

    def trigger(self, *args, **kwargs):
        is_top_device = getattr(self, "parent", None) is None
        if is_top_device:
            # This is the top-level device, so trigger it
            return self._trigger_scaler(*args, **kwargs)
        else:
            # This is a sub-component of a device, so trigger the parent
            return self.parent.trigger()

    def _trigger_scaler(self, *args, **kwargs):
        # Figure out if there's already a trigger active
        previous_status = self._statuses.get(self.scaler_prefix)
        is_idle = previous_status is None or previous_status.done
        # Trigger the detector if not already running, and update the status dict
        if is_idle:
            new_status = super().trigger(*args, **kwargs)
            self._statuses[self.scaler_prefix] = new_status
        else:
            new_status = previous_status
        return new_status


class ScalerSignal(ScalerTriggered, EpicsSignal): ...


class ScalerSignalRO(ScalerTriggered, EpicsSignalRO): ...


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
