############
Fly Scanning
############

.. contents:: Table of Contents
    :depth: 3


Fly scanning is when detectors **take measurements while one or more
positioners are in motion**, creating a range of measurements based on
user specified points. This method is generally faster than
traditional step scanning.

Fly-scanning with Bluesky follows a general three method process

- **Prepare:** Configures the device to fly.
- **Kickoff:** Initializes flyable ophyd-async devices to set themselves up and 
  start scanning.
- **Complete:** Continuously checks whether flight is occurring until it is finished.
- **Collect:** Retrieves data from fly scan as proto-events.

Most of the work that is done for fly scanning is done with
ophyd-async. Bluesky's way of fly scanning requires the ophyd-async
flyer device to have the ``kickoff()``, ``complete()``, ``collect()``,
and ``collect_describe()`` methods. Any calculation or configuration
for fly scanning is done inside the ophyd-async device, though in many
cases this is included with ophyd-async (e.g. area detectors).

Modes of Fly Scanning
=====================

Fly scanning can trigger devices in one of two modes:

1. **Internal** Devices operate and trigger independently.
2. **External** Devices are synchronized at the hardware level.

When using **internal** triggering, the positioners and detectors
operate independently from one another. Typically the positioners are
set to cover a range at a given speed, while detectors repeatedly
acquire data. This approach can be applied to many types of devices,
but the points at which the detector is triggered are not
predictable. While the position at each detector reading will be
known, the positions will not be exactly those specified in the
plan. This fly-scan mode is **best suited for scans where measuring
specific points is not critical**, such as for alignment of optical
components, e.g. slits. Grid scans are possible with internal
triggering, however there is no guarantee that the resulting data
stream can be reconstructed into a grid.

If a movable device supports **external** triggering, the mover's
hardware will produce a signal that is used to directly trigger one or
more detectors. Both the positioner and detectors must have compatible
triggering mechanisms, and the physical connections must be made
before-hand. *External* triggering is **best suited for scans where
the precise position of each detector reading is critical**, such as
for data acquisition. N-dimensional grid scans can also be performed
with *external* triggering in a way that can produce a proper grid.

The fly scanning plans in Haven, such as
:py:func:`haven.plans._fly.fly_scan()`, accept an optional *trigger*
parameter that determines whether internal or external triggering will
be used. Some devices support both *internal* and *external*
triggering. Each device must have its ``prepare()`` method called, and
the argument will describe the triggering mechanism to use.

Many detectors actually expect a **gate** instead of a trigger. A gate
is typically pulled high when acquisition is commanded, and pulled low
otherwise. Such detectors should have a `validate_trigger_info()`
method, which accepts a :py:class:`ophyd_async.core.TriggerInfo`
instance, and returns a new :py:class:`~ophyd_async.core.TriggerInfo`
instance with the closest parameters that the device can
accommodate. It is then up to the plan to decide if this is acceptable,
and to configure the hardware accordingly.

Data Streams
============

With *interal* triggering, each flyable device used in a fly scan will
produce its own data stream with the name of the device. This is
because there no guarantee that the events will line up, or even have
compatible shapes. With *external* triggering, the haven fly-scan
plans will declare as many devices as possible as part of the same
"primary" data stream.


Plans for Fly-Scanning
======================

Haven provides several fly-scanning plans. Each one assumes that
flyers implement Bluesky's :py:class:`~bluesky.protocols.Flyable`
protocol.

``fly_scan()``
--------------

Haven's :py:func:`~haven.plans.fly.fly_scan` mimics the Bluesky
:py:func:`~bluesky.plans.scan` plan, with additional parameters, such
as *dwell_time*, necessary for fly-scanning.

.. code:: python

    from ophyd_async.core import DetectorTrigger
    from haven import plans
    
    # Prepare devices
    aerotech = haven.registry.find("aerotech")
    ion_chambers = haven.registry.findall("ion_chambers")
    # Execute the fly scan
    plan = plans.fly_scan(
        ion_chambers,
	aerotech.horizontal,
	-1000,
	1000,
	num=101,
	dwell_time=0.2,
	trigger=DetectorTrigger.EDGE_TRIGGER,
    )
    RE(plan)
    
Multiple positioners can be flown together by listing additional
*motor*, *start*, *stop* combinations, similar to the step-scanning
equivalent :py:func:`bluesky.plans.scan()`. However, it is not trivial
to coordinate these motions, especially if using *external*
triggering.

``grid_fly_scan()``
-------------------

Haven's :py:func:`~haven.plans.fly.grid_fly_scan()` provides an
N-dimension scan over all combinations of multiple axes, mimicing
Bluesky's :py:func:`~bluesky.plans.grid_scan()` plan. The first motor
listed will be the slow scanning axis, and the last motor listed will
be the flyer. Each motor must have an accompanying *start*, *stop*,
and *num* arguments:

.. code:: python

    from ophyd_async.core import DetectorTrigger
    from haven import plans
    
    # (start, stop, num)
    fly_params = (-100, 100, 21)
    step_params = (-100, 100, 5)

    # Find the devices
    ion_chambers = haven.registry.findall("ion_chambers")
    aerotech = haven.registry.find("aerotech")

    # Set up the plan
    plan = plans.grid_fly_scan(
        ion_chambers,
        aerotech.vert, *step_params,
        aerotech.horiz, *fly_params,
	dwell_time=0.1,
        snake_axes=True,
	trigger="EDGE_TRIGGER",
    )
    # Run the plan
    RE(plan, purpose="testing fly scanning", sample="None")


Aerotech-Stage
==============

The Aerotech stage has a number of axes, for example, ``.horizontal``
and ``.vertical``. Each is a sub-class of
:py:class:`ophyd_async.epics.motor.Motor`, adding the
:py:class:`~ophyd.flyers.FlyerInterface`. Each of these axes can be
used as a flyer in the `plans for fly-scanning`_ provided it is using
the EPICS automation1 module.

Position-Synchronized Output (PSO)
----------------------------------

The Automation1 controller can be configured to emit voltage pulses at
fixed distance intervals. These position-synchronized output (PSO)
pulses are used to trigger hardware to begin a new bin of
measurements. The ophyd-async flyer device sends comands to the
ensemble controller to configure its settings. PSO pulses are sent in
the form of a 25 µs pulse. These pulses are then set to only happen
every multiple integer of encoder step counts, corresponding to the
requested step size.

.. figure:: PSO_diagram.svg
   :alt: Diagram of PSO pulse timing.

   Diagram of PSO pulse timing. Encoder counts are an integer number
   of the smallest unit the controller can measure
   (e.g. nanometers). The distance from one pulse to the next equates
   to new bin on the scaler. Encoder window gives a range outside of
   which PSO pulses will be suppressed. Bottom line shows relative
   positions of key calculated and supplied parameters.
	 
While the scaler can use these raw pules to create a bin, other
detectors have other requirements. Additional hardware, such as a
soft-glue FPGA, is used to transform the pulses to match the
requirements of the various detectors.

.. figure:: fly_scan_block_diagram.svg

   Control flow diagram of how hardware is connected for fly
   scanning. The *trigger* output mimics the trigger input, while the
   length of the delay for the falling edge of the *gate* signal is
   based on the dwell time of the scan.
