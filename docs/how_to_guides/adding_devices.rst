Adding Devices in Haven
=======================

This guide encompasses two concepts:

- adding a new instance of a device that already has Haven support
- adding a new category of device that does not have Haven support

Existing Haven Support
----------------------

If the device you are using already has a device class created for it,
then using the device only requires a suitable entry in the iconfig
file. By inspecting the environmental variable HAVEN_CONFIG_FILES we
can see that in this case the configuration file is
``~/bluesky/iconfig.toml``, though your beamline may be different.

.. code-block:: bash

    $ echo $HAVEN_CONFIG_FILES
    /home/beams/S255IDCUSER/bluesky/iconfig.toml

Next, add a new section for this device. The TOML section name should
be the device category, often a lower-case version of the device
class. Most devices also accept at least the parameter *name*, which
will be used to retrieve the device later from the instrument
registry.

In most cases the key "prefix" should list the IOC prefix, including
the trailing ":". For this example, we will add a simple motor.

.. code-block:: toml

   [[ motor ]]
   prefix = "255idc:m1"
   name = "bpm"
   
Once this section has been added to ``iconfig.toml``, then the device
can be loaded from the instrument registry. No special configuration
is generally necessary.

This device will be loaded once the beamline's load method is called,
though this **usually done automatically** during startup.

.. code-block::

    from haven.instrument import beamline
    await beamline.load()
    bpm_motor = beamline.registry['bpm']


New Haven Support
-----------------

If Haven does not already have support for the device, this will need
to be added. Details on how to create Ophyd and Ophyd-async devices is
beyond the scope of this guide. Assume for this example that there is
a file ``src/haven/devices/toaster.py`` which contains a device class
``Toaster()`` that accepts the parameters *max_power*, *num_slots*,
*prefix*, and *name*.

To let the Haven instrument loader know about this device, edit the
file ``src/haven/instrument.py`` and look for the line like ``beamline
= Instrument({``. Following this line is a mapping of device classes
to their TOML section names. We will now add our new device to this mapping:

.. code-block:: python

    beamline = Instrument({
        ...
	"toaster": Toaster,
	...
    })

The order does not usually matter, though device classes will be
created in the order they are retrieved from this dictionary.

Now the following section can be added to the ``iconfig.toml`` file.

.. code-block:: toml

    [[ toaster ]]
    name = "sunbeam"
    prefix = "255idc:toast:"
    num_slots = 2  # 2-slot toaster
    max_power = 1200  # Watts
