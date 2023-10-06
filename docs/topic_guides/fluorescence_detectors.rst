#######################
Fluorescence Detectors
#######################

The operation of a fluorescence detectors depends on the electronics
used to process the signal coming from the detector head:

- XIA DXP (Xmap, mercury, etc)
- Xspress3

Specifying Detectors in Configuration
=====================================

To add new detectors to the beamline, new sections should be added the
*iconfig.toml* file. The section should be labeled
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

   my_detector = haven.registry.find(name="vortex_me4")
   another_detector = haven.registry.find(name="vortex_ex")


Common Behavior
===============

Fluorescence detectors are implemented as
:py:class:`~haven.instrument.xspress.Xspress3Detector` and
:py:class:`~haven.instrument.dxp.DxpDetector` Ophyd device
classes. They are written to have a common Ophyd interface so that
clients (e.g. Firefly) can use fluorescence detectors interchangeably.

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

XIA DXP
=======

DXP electronics use the bluesky multi-channel analyzer (MCA) device,
packaged in Haven as the
:py:class:`~haven.instrument.fluorescence_detector.DxpDetectorBase`
class.

By default, this device does not include any MCA elements, since the
number of elements varies with each detector. The **recommended way to
create a fluorescence detector** device directly is using DXP
electronics is with the
:py:func:`~haven.instrument.fluorescence_detector.load_dxp_detector`
factory:

.. code-block:: python
   
   from haven import load_dxp_detector
   
   det = load_dxp_detector(name="vortex_me4",
                           prefix="20xmap4b",
		           num_elements=4)
   det.wait_for_connection()

By default all elements (MCAs) will collect spectra, but no ROIs will
save aggregated values. Individual elements and ROI's can be enabled
and disabled using the following methods on the
:py:class:`~haven.instrument.fluorescence_detector.DxpDetectorBase`
object:

- :py:meth:`~haven.instrument.fluorescence_detector.DxpDetectorBase.enable_rois`
- :py:meth:`~haven.instrument.fluorescence_detector.DxpDetectorBase.disable_rois`
- :py:meth:`~haven.instrument.fluorescence_detector.DxpDetectorBase.enable_elements`
- :py:meth:`~haven.instrument.fluorescence_detector.DxpDetectorBase.disable_elements`

These methods accepts an option sequence of integers for the indices
of the elements or ROIs to enable/disable. If not ROIs or elements are
specified, the methods will operate on all ROIs or elements
(e.g. ``det.disables_elements()`` will disable all
elements. **Elements are indexed from 1, while ROIs are indexed from
0** in keeping with the convention in the synApps MCA support.


