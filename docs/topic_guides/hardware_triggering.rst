=====================
 Hardware Triggering
=====================

For simple devices, it is enough to let bluesky and ophyd handle
triggering the detector. In our case, though, many detectors are to be
triggered simultaneously using one piece of hardware.

An example is **using the scaler to trigger multiple pieces of
hardware**. The SIS3820 multi-channel scaler can measure multiple
channels of input with one trigger. If each detector is an ophyd
``Device`` object, then running a bluesky plan with multiple of these
devices on the same scaler will result in the scaler being triggered
multiple times (once for each device in the plan).

Additionally, the scaler presents the counting gate on one of its
control output lines. This can be fed into the Xspress3 electronics
that power many of our Vortex detectors. Bluesky by default will try
to trigger the Xspress3 directly. The ``Device`` definition for the
Vortex detector could trigger the scaler itself, but this creates yet
another trigger signal to the scaler, as described above.

The **solution** is to use the
:py:class:`~haven.devices.scaler_triggered.ScalerTriggered` mixin
class. This adds a *scaler_prefix* argument to ``__init__`` that
expects a channel access PV path and points to the scaler that should
be used to trigger this device. If multiple instances of
:py:class:`~haven.devices.scaler_triggered.ScalerTriggered` with
the same *scaler_prefix* are present in a bluesky plan, then the
scaler is only triggered once for all the devices.

*scaler_prefix* can be omitted, in which case the *prefix* argument
will be used for the scaler prefix.

.. code-block:: python

    from haven.devices.scaler_triggered import ScalerTriggered
    from ophyd import Device

    class VortexDetector(ScalerTriggered, Device):
        ...

    vortex = VortexDetector(prefix="vortex1ioc:vortex", scaler_prefix="25idcVME:scaler1")


 
