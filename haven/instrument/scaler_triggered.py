from ophyd import (
    Device,
    FormattedComponent as FCpt,
    Kind,
)

from ..signal import Signal


__all__ = ["ScalerTriggered"]


class ScalerTriggered:
    _statuses = {}
    count = FCpt(Signal, "{scaler_prefix}.CNT", trigger_value=1, kind=Kind.omitted)

    def __init__(self, prefix="", *, scaler_prefix=None, **kwargs):
        # Determine which prefix to use for the scaler
        if scaler_prefix is not None:
            self.scaler_prefix = scaler_prefix
        else:
            self.scaler_prefix = prefix
        super().__init__(**kwargs)

    def trigger(self, *args, **kwargs):
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
