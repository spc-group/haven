###########################
Area Detectors and Cameras
###########################

Area detectors are all largely the same but with small variations from
device-to-device. All the device definitions for area detectors are in
the :py:mod:`haven.devices.area_detector` module.

Currently supported detectors:

- Eiger 500K (:py:class:`~haven.devices.area_detector.Eiger500K`)
- Lambda (:py:class:`~haven.devices.area_detector.Lambda250K`)
- Simulated detector (:py:class:`~haven.devices.area_detector.SimDetector`)

EPICS and Ophyd do not make a distinction between area detectors and
cameras. After all, a camera is just an area detector for visible
light.

In Haven, the device classes are largely the same. The only
substantive difference is that cameras have the ophyd label "cameras",
whereas non-camera area detectors (e.g. Eiger 500K), have the ophyd
label "area_detectors". They can be used interchangeably in plans.

.. warning::

   Currently, cameras are not properly implemented in Haven. This will
   be fixed soon.

Using Devices in Haven
======================

If the device you are using already has a device class created for it,
then using the device only requires a suitable entry in the iconfig
file (``~/bluesky/instrument/iconfig.toml``). The iconfig section name
should begin with "area_detector", and end with the device name
(e.g. "area_detector.eiger"). The device name will be used to retrieve
the device later from the instrument registry.

The key "prefix" should list the IOC prefix, minus the trailing
":". The key "device_class" should point to a subclass of ophyd's
:py:class:`~ophyd.areadetector.detectors.DetectorBase` class that is
defined in :py:mod:`haven.devices.area_detector`.


.. code-block:: toml

   [area_detector.eiger]

   prefix = "dp_eiger_xrd91"
   device_class = "Eiger500K"
   

Once this section has been added to ``iconfig.toml``, then the device
can be loaded from the instrument registry. No special configuration
is generally necessary.

.. code-block:: python

   >>> import haven
   >>> haven.load_instrument()
   >>> det = haven.registry.find("eiger")
   >>> plan = haven.xafs_scan(..., detectors=[det])

Usually, no special configuration is needed for area detectors. By
default it will save HDF5 and TIFF files for each frame. The filenames
for these TIFF and HDF5 files will be stored automatically to the
database. The outputs of the stats plugins will also be saved.

.. warning::

   It is up you to make sure the file path settings are correct for
   the HDF5 and TIFF NDplugins. Also, ensure that the routing is
   correct for the ROI and STATS NDplugins.

.. warning::

   The first time you stage the device after the IOC has been
   restarted, you may receive an error about the **plugin not being
   primed**. The means that the plugin does not know the size of the
   image to expect since it has not seen one yet. The solution is to
   open the caQtDM panels for the detector, ensure the corresponding
   plugins are enabled, and then manually acquire a frame.
