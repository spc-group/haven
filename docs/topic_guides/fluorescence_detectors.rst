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
``[fluorescence_detector.<name>]``, where ``<name>`` becomes the
device name. *prefix* is the PV prefix for the EPICS IOC,
*electronics* determines whether to use XIA DXP (``"dxp"``) or
Xspress3 (``"xspress3"``) support, and *num_elements* specifies the
number of detector elements.

.. code-block:: toml

   [fluorescence_detector.vortex_me4]

   prefix = "20xmap4b"
   electronics = "dxp"  # or "xspress3"
   num_elements = 4

The device can then be retrieved from the instrument registry for use
in bluesky plans:

.. code-block:: python
   
   import haven

   det = haven.registry.find(name="vortex_me4")


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


Xspress3
========

Support for Xspress3 electronics is not ready yet.
