Instrument Registry for Looking Up Components
=============================================

The **instrument registry** in Haven provides a way to keep track of
the devices (including components, motors, signals, etc.) that have
been defined across the package. In order for the registry to know of
a device, that device must first be registered. Unless you are
defining your own devices or components, this will have already been
done.

It is a goal of this project that **executing simple scans will not
require you to know about or interact directly with the registry.**
However, more advanced scans, like using area detectors from the
command line, may require you to look up devices in the registry prior
to building the scan.

This documentation is provided primarily for developers who are
planning to register their own devices and components.

Looking Up Registered Devices/Components
----------------------------------------

In many cases, Haven will look up devices behind the scenes when
executing a plan. However, it is possible to look up devices directly
using the registry.

The registry uses the built-in concept of device labels in Ophyd. The
registry's
:py:meth:`~haven.devices.instrument_registry.InstrumentRegistry.find()`
and
:py:meth:`~haven.devices.instrument_registry.InstrumentRegistry.findall()`
methods allows devices to be looked up by label or device name. For
example, assuming four devices exist with the label "ion_chamber",
then these devices can be retrieved using the registry:

.. code-block:: python

    from haven import registry

    ion_chambers = registry.find(label="ion_chambers")
    assert len(ion_chambers) == 4

Many plans in Haven accept lists of detectors and positioners. In some
cases, it is possible to pass a string as these parameters as well, in
which case the plan will assume that the string is a device name or
label and find all registered devices that match. The following will
execute the :py:func:`~haven.plans.energy_scan.energy_scan()` plan
using any device initialized with ``labels={"ion_chambers"}`` and
known to the registry.

.. code-block:: python

    from haven import energy_scan

    RE(energy_scan(..., detectors="ion_chambers"))

Looking Up Sub-Components by Dot-Notation
-----------------------------------------

For simple devices, the full name of the sub-component should be
enough to retrieve the device. For example, to find the signal
*preset_time* on the device named "vortex_me4", the following may work fine:

.. code-block:: python

   preset_time = haven.registry.find("vortex_me4_preset_time")

However, **if the component is lazy** and has not been accessed prior
to being registered, then **it will not be available in the
registry**. Sub-components can instead be accessed by dot
notation. Unlike the full device name, dot-notation names only resolve
when the component is requested from the registry, at which point the
lazy components can be accessed.

For example, area detectors use many lazy components. If ``sim_det``
is an area detector with a camera component ``sim_det.cam``, then the
name of the gain channel is "sim_det_cam_gain", however this is a lazy
component so is not available. Instead, retrieving the device by
``haven.registry.find("sim_det.cam.gain")`` will first find the area
detector ("sim_det"), then access the *cam* attribute, and then cam's
*gain* attribute. This has the side-effect of instantiating the lazy
components.

Registering Individual Devices
------------------------------

Before looking up a device in the registry, it is necessary to inform
the registry about the device. The simplest way to do this is using
the
:py:meth:`~haven.devices.instrument_registry.InstrumentRegistry.register()`
method on the registry.

.. code-block:: python

    from ophyd import Device
    from haven import registry

    # Create the device instance
    I0 = Device("PV_PREFIX", name="I0", labels={"ion_chamber"})
    # Register the device with the registry
    registry.register(I0)

    # Or more concisely in 1 line
    It = registry.register(Device("PV_PREFIX", name="It", labels={"ion_chamber"}))

Registering Device Classes
--------------------------

If you are creating many instances of a custom Device subclass,
registering each instance individually can be repetitive. Haven allows
you to modify the class itself so that each instance is automatically
registered. This is accomplished using the
:py:meth:`~haven.devices.instrument_registry.InstrumentRegistry.register`
method as a decorator on the class:

.. code-block:: python

    from ophyd import Device
    from haven import registry

    @registry.register
    class IonChamber(Device):
        ...

    I0 = IonChamber(..., labels={"ion_chamber"})

This is equivalent to the examples for registering individual devices
above.

Creating Your Own Registry
--------------------------

There is nothing special about
:py:obj:`haven.devices.instrument_registry.registry`; it is simply
an instance of
:py:class:`haven.devices.instrument_registry.InstrumentRegistry`
created during module import as a default. Most of the devices and
components defined in Haven register themselves with this default
registry. However, there's nothing to prevent you from creating your
own registry:

.. code-block:: python

    from haven import InstrumentRegistry
    from ophyd import Device
    
    # Create an empty registry
    my_registry = InstrumentRegistry()
    
    # Create a new registered device object
    my_device = my_registry.register(Device("PV_PREFIX", name="My Device", labels={"custom"}))
    
    # Now look for this device in the registry
    my_devices = my_registry.find(label="custom")

Design Defense
--------------

This pattern touches on behavior already present in bluesky and
apstools. However, there are some quirks that make these
implementations unsuitable for use in Haven.

Bluesky provides the ``%wa`` IPython magic to list devices (apstools
has a similar ``listobjects()`` function). While conventient when
working in an IPython environment, this comes with a number of
drawbacks for Haven. First, ``%wa`` only knows about devices listed in
the local context of the IPython interpreter. If a device is defined
in the file *devices.py*, the method of importing will determine
whether the device is visible or not:

.. code-block:: python
   :caption: devices.py

    from ophyd import Device

    I0 = Device("PV_PREFIX", name="I0", labels={"ion_chamber"})

.. code-block:: python
   :caption: IPython shell

    >>> import devices
    >>> print(devices.I0)
    >>> %wa  # This will not include I0
    >>> from devices import I0
    >>> print(I0)
    >>> %wa  # Now I0 is included
    
This detail makes it impossible to run plans without knowing about all
the devices and importing them individually, or else using star
imports (e.g. ``from devices import *``) which make tracing imports
difficult and leads to cluttered namespaces.

Furthermore, this approach is tightly coupled to IPython, since it
relies on the IPython shell's namespace to find devices. The above
approach is not possible with vanilla CPython.

It may be possible to use ``locals()`` instead of the IPython shell
namespace, solving the reliance on IPython. This still leaves the
issue of only having access to devices imported directly into the
shell's namespace, however. This could be solved by recursively
descending into imported modules looking for devices. Here, PEP 20
steers us towards the registry-based solution, where we must
explicitely define a device as being included in the registry
("explicit is better than implicit").
