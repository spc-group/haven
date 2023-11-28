import asyncio

from epics import PV


async def caget(pvname: str, timeout: float = 2.0):
    """Asynchronous wrapper around pyepics.caget.

    Returns
    =======
    value
      Current PV value retrieved from the IOC.

    """
    loop = asyncio.get_running_loop()
    future = loop.create_future()

    # Callback for when the value changes
    def check_value(pvname, value, status, **kwargs):
        if status is None:
            # Not a real update
            return
        elif status == 0:
            future.set_result(value)
        else:
            exc = RuntimeError(f"Could not caget value for PV {pvname}")
            future.set_exception(exc)

    # Wait for the real value to come in from the IOC
    pv = PV(pvname, callback=check_value, auto_monitor=True)
    await asyncio.wait_for(future, timeout=timeout)
    # Clean up
    del pv
    return future.result()


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
