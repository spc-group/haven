from typing import Optional
import logging


from haven import exceptions
from haven.typing import Detector


log = logging.getLogger(__name__)


__all__ = ["InstrumentRegistry", "registry"]


class InstrumentRegistry:
    """A registry keeps track of devices, signals, etc that have been
    previously registered.

    This mimics the %wa bluesky magic behavior, except that devices
    can be registered outside of the main REPL loop.

    """

    devices = []  # Replaced during __init__() since [] is mutable

    def __init__(self):
        self.components = []

    def find(self, label: Optional[str] = None):
        """Find registered device components matching parameters."""
        try:
            results = [
                cpt
                for cpt in self.components
                if label in getattr(cpt, "_ophyd_labels_", [])
            ]
        except TypeError:
            raise exceptions.InvalidComponentLabel(label)
        # Check that the label is actually defined somewhere
        if len(results) == 0:
            raise exceptions.ComponentNotFound(
                f"Could not find components matching label: {label}"
            )
        return results

    def __new__wrapper(self, cls, *args, **kwargs):
        # Create and instantiate the new object
        obj = super(type, cls).__new__(cls)
        obj.__init__(*args, **kwargs)
        # Register the new object
        self.register(obj)
        return obj

    def register(self, component: Detector) -> Detector:
        """Register a device, component, etc so that it can be retrieved later.

        If *component* is a class, then any instances created will
        automatically be registered. Else, *component* will be assumed
        to be an instance and will be registered directly.

        Returns
        =======
        component
          The same component as was provided as an input.

        """
        if isinstance(component, type):
            # A class was given, so instances should be auto-registered
            component.__new__ = self.__new__wrapper
        else:
            # An instance was given, so just save it in the register
            self.components.append(component)
        return component


registry = InstrumentRegistry()
