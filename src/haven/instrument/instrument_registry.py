from typing import Optional, Sequence
import logging
import warnings
from itertools import chain

from ophyd import Component, ophydobj

from .. import exceptions
from .._iconfig import load_config
from ..typing import Detector


log = logging.getLogger(__name__)


__all__ = ["InstrumentRegistry", "registry"]


def is_iterable(obj):
    return (not isinstance(obj, str)) and hasattr(obj, "__iter__")


def remove_duplicates(items, key=None):
    unique_items = list()
    for item in items:
        val = item if key is None else key(item)
        if val not in unique_items:
            yield item
            unique_items.append(val)


class InstrumentRegistry:
    """A registry keeps track of devices, signals, etc that have been
    previously registered.

    This mimics the %wa bluesky magic behavior, except that devices
    can be registered outside of the main REPL loop.

    """

    components: Sequence

    def __init__(self):
        self.clear()

    def clear(self):
        """Remove the previously registered components."""
        self.components = []

    @property
    def component_names(self):
        return [c.name for c in self.components]

    @property
    def device_names(self):
        return [c.name for c in self.components if c.parent is None]

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

        The name provided to *any_of*, *label*, or *name* can also
        include dot-separated attributes after the device name. For
        example, looking up ``name="eiger_500K.cam.gain"`` will look
        up the device named "eiger_500K" then return the
        Device.cam.gain attribute.

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
        results = list(
            self.findall(any_of=any_of, label=label, name=name, allow_none=allow_none)
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

    def _findall_by_label(self, label, allow_none):
        # Check for already created ophyd objects (return as is)
        if isinstance(label, ophydobj.OphydObject):
            yield label
            return
        # Recursively get lists of components
        if is_iterable(label):
            for lbl in label:
                yield from self.findall(label=lbl, allow_none=allow_none)
        else:
            # Split off label attributes
            try:
                label, *attrs = label.split(".")
            except AttributeError:
                attrs = []
            try:
                for cpt in self.components:
                    if label in getattr(cpt, "_ophyd_labels_", []):
                        # Re-apply the dot-notation attributes
                        cpt_ = cpt
                        for attr in attrs:
                            cpt_ = getattr(cpt_, attr)
                        yield cpt_
            except TypeError:
                raise exceptions.InvalidComponentLabel(label)

    def _findall_by_name(self, name):
        # Check for already created ophyd objects (return as is)
        if isinstance(name, ophydobj.OphydObject):
            yield name
            return
        # Check for an edge case with EpicsMotor objects (user_readback name is same as parent)
        try:
            is_user_readback = name[-13:] == "user_readback"
        except TypeError:
            is_user_readback = False
        if is_user_readback:
            parentname = name[:-14].strip("_")
            yield self.find(name=parentname).user_readback
        elif is_iterable(name):
            for n in name:
                yield from self.findall(name=n)
        else:
            # Split off any dot notation parameters for later filtering
            try:
                name, *attrs = name.split(".")
            except AttributeError:
                attrs = []
            # Find the matching components
            for cpt in self.components:
                if cpt.name == name:
                    cpt_ = cpt
                    # Re-apply dot-notation filter
                    for attr in attrs:
                        cpt_ = getattr(cpt_, attr)
                    yield cpt_

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

        The name provided to *any_of*, *label*, or *name* can also
        include dot-separated attributes after the device name. For
        example, looking up ``name="eiger_500K.cam.gain"`` will look
        up the device named "eiger_500K" then return the
        Device.cam.gain attribute.

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
        _name = name if name is not None else any_of
        # Apply several filters against label, name, etc.
        if is_iterable(any_of):
            for a in any_of:
                results.append(self.findall(any_of=a, allow_none=allow_none))
        else:
            # Filter by label
            if _label is not None:
                results.append(self._findall_by_label(_label, allow_none=allow_none))
            # Filter by name
            if _name is not None:
                results.append(self._findall_by_name(_name))
        # Peek at the first item to check for an empty result
        results = chain(*results)
        try:
            first = next(results)
        except StopIteration:
            # No results were found
            if allow_none:
                results = []
            else:
                raise exceptions.ComponentNotFound(
                    f'Could not find components matching: label="{_label}", name="{_name}"'
                )
        else:
            # Stick the first entry back in the queue and yield it
            results = chain([first], results)
        return remove_duplicates(results)

    def __new__wrapper(self, cls, *args, **kwargs):
        # Create and instantiate the new object
        obj = super(type, cls).__new__(cls)
        obj.__init__(*args, **kwargs)
        # Register the new object
        self.register(obj)
        return obj

    # @profile
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
        beamline_is_connected = load_config()["beamline"]["is_connected"]
        # Determine how to register the device
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
            # Test the connection to ensure the device is present
            if beamline_is_connected and component.parent is None:
                try:
                    component.wait_for_connection()
                except TimeoutError as exc:
                    msg = f"Could not connect to device {component.name} ({component.prefix})"
                    log.warning(msg)
                    return component
            # Register this component
            self.components.append(component)
            # Recusively register sub-components
            sub_signals = getattr(component, "_signals", {})
            for cpt_name, cpt in sub_signals.items():
                self.register(cpt)
        return component


registry = InstrumentRegistry()
