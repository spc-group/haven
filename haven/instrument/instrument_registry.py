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
        """Remove the previously registered components."""
        self.components = []

    @property
    def component_names(self):
        return [c.name for c in self.components]

    def find(
        self,
        any_of: Optional[str] = None,
        *,
        label: Optional[str] = None,
        name: Optional[str] = None,
        allow_none: Optional[str] = False,
    ) -> Component:
        """Find registered device components matching parameters.

        The *any_of* keyword is a proxy for all the other
        keywords. For example ``findall(any_of="my_device")`` is
        equivalent to ``findall(name="my_device",
        label="my_device")``.

        Parameters
        ==========
        any_of
          Search by all of the other parameters.
        label
          Search by the component's ``labels={"my_label"}`` parameter.
        name
          Search by the component's ``name="my_name"`` parameter.
        allow_none
          If false, missing components will raise an exception. If
          true, an empty list is returned if no registered components
          are found.


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
        results = self.findall(
            any_of=any_of, label=label, name=name, allow_none=allow_none
        )
        if len(results) == 1:
            result = results[0]
        elif len(results) > 1:
            raise exceptions.MultipleComponentsFound(
                f"Found {len(results)} components matching query "
                f"[any_of={any_of}, label={label}, name={name}]. "
                "Consider using ``findall()``. "
                f"{results}"
            )
        else:
            result = None
        return result

    def findall(
        self,
        any_of: Optional[str] = None,
        *,
        label: Optional[str] = None,
        name: Optional[str] = None,
        allow_none: Optional[bool] = False,
    ) -> Sequence[Component]:
        """Find registered device components matching parameters.

        Combining search terms works in an *or* fashion. For example,
        ``findall(name="my_device", label="ion_chambers")`` will find
        all devices that have either the name "my_device" or a label
        "ion_chambers".

        The *any_of* keyword is a proxy for all the other keywords. For
        example ``findall(any_of="my_device")`` is equivalent to
        ``findall(name="my_device", label="my_device")``.

        Parameters
        ==========
        any_of
          Search by all of the other parameters.
        label
          Search by the component's ``labels={"my_label"}`` parameter.
        name
          Search by the component's ``name="my_name"`` parameter.
        allow_none
          If false, missing components will raise an exception. If
          true, an empty list is returned if no registered components
          are found.

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
        results = []
        # If using *any_of*, search by label and name
        _label = label if label is not None else any_of
        # Define a helper to test for lists of search parameters
        _name = name if name is not None else any_of

        def is_iterable(obj):
            return (not isinstance(obj, str)) and hasattr(obj, "__iter__")

        if is_iterable(any_of):
            for a in any_of:
                results.extend(self.findall(any_of=a, allow_none=allow_none))
        else:
            # Filter by label
            if _label is not None:
                if is_iterable(_label):
                    [
                        results.extend(self.findall(label=lbl, allow_none=allow_none))
                        for lbl in _label
                    ]
                else:
                    try:
                        results.extend(
                            [
                                cpt
                                for cpt in self.components
                                if _label in getattr(cpt, "_ophyd_labels_", [])
                            ]
                        )
                    except TypeError:
                        raise exceptions.InvalidComponentLabel(_label)
            # Filter by name
            if _name is not None:
                if is_iterable(_name):
                    [results.extend(self.findall(name=n)) for n in _name]
                results.extend([cpt for cpt in self.components if cpt.name == _name])
        # If a query term is itself a device, just return that
        found_results = len(results) > 0
        if not found_results:
            for obj in [_label, _name, any_of]:
                if isinstance(obj, ophydobj.OphydObject):
                    results = [obj]
                    break
        # Check that the label is actually defined somewhere
        found_results = len(results) > 0
        if not found_results and not allow_none:
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
            # Ignore any instances with the same name as a previous component
            # (Needed for some sub-components that are just readback
            # values of the parent)
            duplicate_components = [
                c for c in self.components if c.name == component.name
            ]
            # Check that we're not adding a duplicate component name
            is_duplicate = component.name in [c.name for c in self.components]
            if is_duplicate:
                msg = f"Ignoring components with duplicate name: '{component.name}'"
                log.debug(msg)
                return component
            # Register this component
            self.components.append(component)
            # Recusively register sub-components
            sub_signals = getattr(component, "_signals", {})
            for attr_name, cpt in sub_signals.items():
                self.register(cpt)
        return component


registry = InstrumentRegistry()
