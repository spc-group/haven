import asyncio

import numpy as np
from bluesky.protocols import Movable, Stoppable

from ophyd_async.core import (
    CALCULATE_TIMEOUT,
    DEFAULT_TIMEOUT,
    AsyncStatus,
    CalculatableTimeout,
    ConfigSignal,
    Device,
    HintedSignal,
    StandardReadable,
    WatchableAsyncStatus,
    WatcherUpdate,
    observe_value,
)
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw, epics_signal_x


class Positioner(StandardReadable, Movable, Stoppable):
    """A positioner that has separate setpoint and readback signals.

    Parameters
    ==========
    name:
      The device name for this positioner.
    """

    def set_name(self, name: str):
        super().set_name(name)
        # Readback should be named the same as its parent in read()
        self.readback.set_name(name)

    @WatchableAsyncStatus.wrap
    async def set(self, value: float, timeout: CalculatableTimeout = CALCULATE_TIMEOUT):
        new_position = value
        self._set_success = True
        old_position, units, precision, velocity = await asyncio.gather(
            self.setpoint.get_value(),
            self.units.get_value(),
            self.precision.get_value(),
            self.velocity.get_value(),
        )
        if timeout == CALCULATE_TIMEOUT:
            assert velocity > 0, "Mover has zero velocity"
            timeout = abs(new_position - old_position) / velocity + DEFAULT_TIMEOUT
        # Make an Event that will be set on completion, and a Status that will
        # error if not done in time
        reached_setpoint = asyncio.Event()
        done_event = asyncio.Event()

        def watch_done(value):
            if value == self.done_value:
                done_event.set

        # Start the move
        if hasattr(self, "actuate"):
            # Set the setpoint, then click "go"
            await self.setpoint.set(new_position, wait=True)
            await self.actuate.trigger(wait=False)
        else:
            # Wait for the value to set, but don't wait for put completion callback
            await self.setpoint.set(new_position, wait=False)
        # Set up status to keep track of when the move is done
        if hasattr(self, "done") and False:  # Disabled insce the timing is wrong
            # Monitor the `done` signal
            self.done.subscribe_value(watch_done)
            done_status = AsyncStatus(asyncio.wait_for(done_event.wait(), timeout))
        else:
            # Monitor based on readback position
            done_status = AsyncStatus(
                asyncio.wait_for(reached_setpoint.wait(), timeout)
            )            
        # Monitor the position of the readback value
        async for current_position in observe_value(
            self.readback, done_status=done_status
        ):
            yield WatcherUpdate(
                current=current_position,
                initial=old_position,
                target=new_position,
                name=self.name,
                unit=units,
                precision=precision,
            )
            # Check if the move has finished
            if np.isclose(current_position, new_position):
                reached_setpoint.set()
                break
        if not self._set_success:
            raise RuntimeError("Motor was stopped")

    async def stop(self, success=True):
        self._set_success = success
        status = self.stop_signal.trigger()
        await status
