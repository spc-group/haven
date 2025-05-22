###########################
Area Detectors and Cameras
###########################

Area detectors are all largely the same but with small variations from
device-to-device. All area detectors are the newer
(awaitable) device definitions based on ophyd-async. They can be found in the
:pyd:mod:`haven.devices.detectors` package.

Currently supported detectors:

- Eiger (e.g. 500K) (:py:class:`~haven.devices.detector.eiger.EigerDetector`)
- Lambda Flex and 250K (:py:class:`~haven.devices.detector._lambda.LambdaDetector`)
- Simulated detector (:py:class:`~haven.devices.detectors.sim_detector.SimDetector`)
- Aravis cameras (:py:class:`~haven.devices.detectors.aravis.AravisDetector`)

EPICS and Ophyd do not make a distinction between area detectors and
cameras. After all, a camera is just an area detector for visible
light.

In Haven, the device classes are largely the same. The only
substantive difference is that cameras have the ophyd label "cameras",
whereas non-camera area detectors (e.g. Eiger 500K), have the ophyd
label "area_detectors". They can be used interchangeably in plans.

Data saving is handled automatically by the Ophyd-async device. For
Tiled to read the HDF5 file properly, it may be necessary to set the
"Dim 2 Chunk Size" PV in the detectors HDF5 NDFilePlugin to ``1``.
