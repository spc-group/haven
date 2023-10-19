#######################
Fluorescence Detectors
#######################

.. contents:: Table of Contents
    :depth: 3

Specifying Detectors in Configuration
=====================================

To add new detectors to the beamline, new sections should be added the
*iconfig.toml* file. Each section should be labeled
``[<class>.<name>]``, where ``<class>`` specifies which interface is
present (``"dxp"`` for XIA DXP or ``"xspress"`` for Xspress3), and
``<name>`` becomes the device name. *prefix* is the PV prefix for the
EPICS IOC, and *num_elements* specifies the number of detector
elements.

.. code-block:: toml

   [dxp.vortex_me4]

   prefix = "20xmap4b"
   num_elements = 4

   [xspress.vortex_ex]

   prefix = "dp_xsp3_2"
   num_elements = 1


The device can then be retrieved from the instrument registry for use
in bluesky plans:

.. code-block:: python
   
   import haven

   # Get individual fluorescence detectors
   my_detector = haven.registry.find(name="vortex_me4")
   another_detector = haven.registry.find(name="vortex_ex")

   # Get all fluorescence detectors of any kind (e.g. DXP, Xspress3, etc.)
   detectors = haven.registry.findall(label="fluorescence_detectors")


Common Behavior
===============

Fluorescence detectors are implemented as
:py:class:`~haven.instrument.xspress.Xspress3Detector` and
:py:class:`~haven.instrument.dxp.DxpDetector` Ophyd device
classes. They are written to have a common Ophyd interface so that
clients (e.g. Firefly) can use fluorescence detectors interchangeably.

Creating Devices
----------------

By default, devices created from these device classes include one MCA
element, available on the ``mcas`` attribute. The **recommended way to
create a fluorescence detector** device directly is with the
:py:func:`~haven.instrument.dxp.load_xspress()` and
:py:func:`~haven.instrument.dxp.load_dxp()` factory functions:

.. code-block:: python
   
   from haven import load_xspress
   
   det = load_xspress(name="vortex_me4",
		      prefix="20xmap4b",
		      num_elements=4)
   det.wait_for_connection()

Alternately, to make a dedicated subclass with a specific number of
elements, override the ``mcas`` attributes:

.. code-block:: python

    from haven.instrument import xspress

    class Xspress4Element(xspress.Xspress3Detector):
        mcas = xspress.DDC(
            xspress.add_mcas(range_=range(4)),
            kind=(Kind.normal | Kind.config),
            default_read_attrs=["mca0", "mca1", "mca2", "mca3"],
            default_configuration_attrs=["mca0", "mca1", "mca2", "mca3"],
        )

Managing Elements and ROIs
--------------------------

.. note::

   Not all fluorescence detector IOCs agree on how to number MCAs and
   ROIs. To maintain a unified interface, Haven uses the convention to
   start counting from 0 regardless of the IOC. As such, the haven
   device signals may be misaligned with the PVs they map to.

   For example on a DXP-based IOC, an ophyd signal
   ``det.mcas.mca1.rois.roi1`` will have a PV like
   ``xmap_4b:MCA1.R0``.

By default all elements (MCAs) will collect spectra, and **all ROIs
will save aggregated values**. While this setup ensures that no data
are lost, it also creates a large number of signals in the database
and may make analysis tedious. Most likely, only some ROIs are
meaningful, so those signals can be identified by giving them the
``hinted`` kind.

https://blueskyproject.io/ophyd/user/reference/signals.html#kind

During the staging phase (in its
:py:meth:`~have.instrument.fluorescence_detector.ROIMixin.stage()`
method), each ROI will check this signal and if it is true, then it
**will change its kind** to ``hinted``. When unstaging, the signal is
reset to its original value.

Individual **ROIs can be marked for hinting** by setting the
:py:attr:`~haven.instrument.xspress.ROI.use` signal:

.. code-block:: python
   
    from haven import load_xspress

    # Create a Xspress3-based fluorescence detector
    det = load_xspress(name="vortex_me4",
		       prefix="20xmap4b",
    		       num_elements=4)
    
    # Mark the 3rd element, 2nd ROI (0-indexed)
    det.mcas.mca2.rois.roi1.use.set(1)

Behind the scenes, to track the state of
:py:attr:`~haven.instrument.xspress.ROI.use` we add a "~" to the start
of the value in the
:py:meth:`~have.instrument.fluorescence_detector.label` signal if
:py:meth:`~have.instrument.fluorescence_detector.use` is false.
		

Marking multiple ROIs on multiple elements is possible using the
following methods on the
:py:class:`~haven.instrument.fluorescence_detector.XRFMixin` object:

- :py:meth:`~haven.instrument.fluorescence_detector.XRFMixin.enable_rois`
- :py:meth:`~haven.instrument.fluorescence_detector.XRFMixin.disable_rois`

These methods accepts an optional sequence of integers for the indices
of the elements or ROIs to enable/disable. If not ROIs or elements are
specified, the methods will operate on all ROIs or elements
(e.g. ``det.disables_rois()`` will disable all ROIs on all elements.

.. code-block:: python
   
    from haven import load_xspress

    # Create a Xspress3-based fluorescence detector
    det = load_xspress(name="vortex_me4",
		       prefix="20xmap4b",
    		       num_elements=4)
    
    # Mark all ROIs on the third and fifth elements
    det.enable_rois(elements=[2, 4])

    # Unmark the first, eight, and fifteeth elements
    det.enable_rois(rois=[0, 7, 14])

    # Unmark the third ROI on the second element
    det.enable_rois(rois=[2], elements=[1])


XIA DXP
=======

DXP electronics use the bluesky multi-channel analyzer (MCA) device,
packaged in Haven as the
:py:class:`~haven.instrument.fluorescence_detector.DxpDetectorBase`
class.

