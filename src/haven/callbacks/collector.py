from bluesky.callbacks import CollectThenCompute
from bluesky.callbacks.core import make_class_safe


@make_class_safe
class Collector(CollectThenCompute):
    """A callback that just collects events for later consumption.

    Event data can be accessed by providing the signal name in square
    brackets: e.g. ``collector["motorA"]`` to get the motorA readback
    values.

    """

    def compute(self):
        """Does nothing.

        We don't actually need to computer anything, just to keep
        track of events.

        """
        pass

    def __getitem__(self, name: str):
        data = [event["data"][name] for event in self._events]
        return data
