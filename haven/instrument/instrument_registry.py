from typing import Optional, Sequence
import logging

from ophyd import Component, ophydobj

from .. import exceptions
from ..typing import Detector


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
        self.clear()

    def clear(self):
        self.components = []

    @property
    def component_names(self):
        return [c.name for c in self.components]

    def find(
            self, any: Optional[str] = None, *, label: Optional[str] = None, name: Optional[str] = None
    ) -> Component:
        """Find registered device components matching parameters.

        Parameters
        ==========
        label
          Search by the component's ``labels={"my_label"}`` parameter.
        name
          Search by the component's ``name="my_name"`` parameter.

        Returns
        =======
        result
          A list of all the components matching the search parameters.

        Raises
        ======
        ComponentNotFound
          No component was found that matches the given search
          parameters.
        MultipleComponentsFound
          The search parameters matched with more than one registered
          component. Either refine the search terms or use the
          ``self.findall()`` method.

        """
        results = self.findall(any=any, label=label, name=name)
        if len(results) > 1:
            raise exceptions.MultipleComponentsFound(
                f"Found {len(results)} components matching query. Consider using ``findall()``."
            )
        else:
            return results[0]

    def findall(
        self,
        any: Optional[str] = None,
        *,
        label: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Sequence[Component]:
        """Find registered device components matching parameters.

        Combining search terms works in an *or* fashion. For example,
        ``findall(name="my_device", label="ion_chambers")`` will find
        all devices that have either the name "my_device" or a label
        "ion_chambers".

        The *any* keyword is a proxy for all the other keywords. For
        example ``findall(any="my_device")`` is equivalent to
        ``findall(name="my_device", label="my_device")``.

        Parameters
        ==========
        any
          Search by all of the other parameters.
        label
          Search by the component's ``labels={"my_label"}`` parameter.
        name
          Search by the component's ``name="my_name"`` parameter.

        Returns
        =======
        results
          A list of all the components matching the search parameters.

        Raises
        ======
        ComponentNotFound
          No component was found that matches the given search
          parameters.

        """
        # Check that we're searching for something
        results = []  # self.components.copy()
        # Filter by label
        _label = label if label is not None else any
        if _label is not None:
            try:
                results.extend(
                    [
                        cpt
                        for cpt in self.components
                        if _label in getattr(cpt, "_ophyd_labels_", [])
                    ]
                )
            except TypeError:
                raise exceptions.InvalidComponentLabel(label)
        # Filter by name
        _name = name if name is not None else any
        if _name is not None:
            results.extend([cpt for cpt in self.components if cpt.name == _name])
        # If a query term is itself a device, just return that
        found_results = len(results) > 0
        if not found_results:
            for obj in [_label, _name, any]:
                if isinstance(obj, ophydobj.OphydObject):
                    results = [obj]
                    break
        # Check that the label is actually defined somewhere
        found_results = len(results) > 0
        if not found_results:
            raise exceptions.ComponentNotFound(
                f'Could not find components matching: label="{_label}", name="{_name}"'
            )
        return list(set(results))

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
        else:  # An instance was given, so just save it in the register
            # Forget about any previously registered instances with the same name
            # (Needed for some sub-components that are just readback values of the parent)
            duplicate_components = [c for c in self.components if c.name == component.name]
            # if "I0" in [c.name for c in duplicate_components]:
            # if component.name == "I0":
            #     import pdb; pdb.set_trace()
            self.components = [c for c in self.components if c not in duplicate_components]
            if len(duplicate_components) > 0:
                log.debug(f"Replacing registered components with {component.name}:",
                          ", ".join([c.name for c in duplicate_components]))
            # Register this component
            self.components.append(component)
            # Recusively register sub-components
            sub_signals = getattr(component, "_signals", {})
            for attr_name, cpt in sub_signals.items():
                self.register(cpt)
        return component


registry = InstrumentRegistry()
