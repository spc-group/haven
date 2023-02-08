from ophyd import (
    Device,
    Component,
    FormattedComponent,
    EpicsSignal,
    EpicsSignalRO,
)


__all__ = ["ScalerTriggered"]


class ScalerTriggered():
    scaler_prefix = None
    _statuses = {}
    
    def trigger(self, *args, **kwargs):
        is_top_device = getattr(self, 'parent', None) is None
        if is_top_device:
            # This is the top-level device, so trigger it
            return self._trigger_scaler(*args, **kwargs)
        else:
            # This is a sub-component of a device, so trigger the parent
            self.parent.trigger()

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


class ScalerSignal(ScalerTriggered, EpicsSignal):
    ...
    
class ScalerSignalRO(ScalerTriggered, EpicsSignalRO):
    ...
