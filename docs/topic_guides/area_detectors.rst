###########################
Area Detectors and Cameras
###########################

Area detectors are all largely the same but with small variations from
device-to-device. Old (threaded) device definitions for area detectors
are in the :py:mod:`haven.devices.area_detector` module. Newer
(awaitable) device definitions are in the
:pyd:mod:`haven.devices.detectors` package.

Currently supported detectors:

- Eiger 500K (:py:class:`~haven.devices.area_detector.Eiger500K`)
- Lambda (:py:class:`~haven.devices.area_detector.Lambda250K`)
- Simulated detector (:py:class:`~haven.devices.detectors.sim_detector.SimDetector`)

EPICS and Ophyd do not make a distinction between area detectors and
cameras. After all, a camera is just an area detector for visible
light.

In Haven, the device classes are largely the same. The only
substantive difference is that cameras have the ophyd label "cameras",
whereas non-camera area detectors (e.g. Eiger 500K), have the ophyd
label "area_detectors". They can be used interchangeably in plans.

.. warning::

   The first time you stage the device after the IOC has been
   restarted, you may receive an error about the **plugin not being
   primed**. The means that the plugin does not know the size of the
   image to expect since it has not seen one yet. The solution is to
   open the caQtDM panels for the detector, ensure the corresponding
   plugins are enabled, and then manually acquire a frame.
