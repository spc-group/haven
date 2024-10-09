#########################
Instrument Configuration
#########################

.. contents:: Table of Contents
    :depth: 3

This page describes the procedure for defining the beamline
configuration. Haven contains definitions for many Ophyd and
Ophyd-async devices, however **Haven needs a beamline configuration
file** to know which specific devices are needed for each beamline.

These files should be **listed in the environmental variable**
``HAVEN_CONFIG_FILES`` as a semi-colon separated list (e.g. ``export
HAVEN_CONFIG_FILES=$HOME/bluesky/iconfig.toml:/local/bluesky/iconfig_extra.toml``).

Then the devices defined in these files can be loaded in python:

.. code-block:: python

    from haven import beamline
    await beamline.load()

Once the beamline has been loaded, the devices are available using an
Ophyd registry attached to the beamline object. For example,
``beamline.registry["austin"]`` would return an Ophyd device instance
named *"austin"*, and ``beamline.registry.findall("ion_chambers")``
would return all devices with the "ion_chambers" Ophyd label.


Motivation
----------

Haven's goal is to **provide support for all of the spectroscopy
beamlines**. However, each beamline is different, and these
differences are **managed by a set of configuration files**, similar
to the .ini files used in the old LabView applications. To keep the
complexity of these configuration files manageable, Haven gets much of
the needed information from the IOCs directly.

The job of processing the configuration files is handled by the
:py:class:`~haven.instrument.Instrument` class. This class keeps track
of the configuration file schema, as well as the resulting devices.

Haven/Firefly should always load without a specific configuration
file, but will probably not do anything useful.


Device Definitions
------------------

The beamline instrument loader can either instantiate ophyd devices
directly, or using factory functions.


Simple Devices
^^^^^^^^^^^^^^

Each device class has an entry in the
:py:object:`~haven.instrument.beamline` loader. To create a new
device, add a table to the configuration file for each device instance
to create. The keys in the table should correspond to arguments passed
to the device's ``__init__()`` method.

Typically, the key for the table is the joined-lower version of the
class name. For example, an instance of the
:py:class:`~haven.devices.mirrors.HighHeatLoadMirror` device class
would be added to the configuration file as:

.. code-block:: toml

   [[ high_heat_load_mirror ]]
   name = "ORM1"
   prefix = "255ida:ORM1:"
   bendable = false

The instrument loader will then create a new device as
``HighHeatLoadMirror(name="ORM1", prefix="255ida:", bendable=False)``.

The resulting device can then be retrieved from the beamline
instrument registry: ``beamline.registry["ORM1"]``.

.. note::

    The Ophyd registry allows looking up devices by Ophyd
    label. E.g. ``beamline.registry.findall("ion_chambers")`` will
    retrieve all devices with *"ion_chambers"* in its labels.

    The instrument loader itself does not handle labels. In most
    cases, reasonable defaults should be set by the device's
    ``__init__()`` methods, however for more control the device table
    could also contain the *labels* key, with the beamline then being
    responsible for ensuring these labels are correct.

    For example, the following device would be accesible by
    ``registry['I0']`` and ``registry.findall("detectors")``, but not
    by ``registry.findall(["ion_chambers"])``

    .. code-block:: toml

        [[ ion_chamber ]]
	name = "I0"
	...
	labels = ["detectors"]


Factory Functions
^^^^^^^^^^^^^^^^^

Devices can be created using functions instead of
:py:class:`~ophyd.Device` classes. The general idea is the same. For
each factory function, the instrument loader will look for tables with
arguments to this function, typically derived from the joined-lower
name for the factory. For example, the function:

.. code-block:: python

    def make_area_detector(name: str, prefix: str, ad_version: str = "4.3") -> Device:
         ...

could have an entry in the configuration file:

.. code-block:: toml

    [[ area_detector ]]
    name = "sim_det"

These factory functions should return either a **new Device**, or a
**iterable of new devices**.
    

Development and Testing
-----------------------

While adding features and tests to Haven, it is often necessary to
read a configuration file, for example when testing functions that
load devices through
:py:func:`~haven.load_instrument.load_instrument()`. However,
the configuration that is loaded should not come from a real beamline
configuration or else there is a risk of controlling real hardware
while running tests.

To avoid this problem, **pytest modifies the configuration file
loading** when running tests with pytest:

1. Ignore any config files besides ``iconfig_default.toml``.
2. Add ``iconfig_testing.toml`` to the configuration

Additionally, all ``load_motors()`` style functions should accept an
optional *config* argument, that will determine the configuration
instead of using the above-mentioned priority.

If a feature is added to Haven that would benefit from
beamline-specific configuration, it can be added in one of two places.

``src/haven/iconfig_default.toml``
  This is the best choice if the device or feature is critical to the
  operation of Haven and/or Firefly, such as the beamline scheduling
  system. The values listed should still not point at real hardware,
  but should be sensible defaults or dummy values to allow Haven to
  function.
``src/haven/iconfig_testing.toml``
  This is the best choice if the device or hardware is optional, and may
  or may not be present at any given beamline, for example,
  fluorescence detectors. This configuration should not point to real
  hardware.


Checking Configuration
----------------------

If Haven is installed with pip, the command ``haven_config`` can be
used to read configuration variables as they will be seen by Haven:

.. code:: bash

	  $ haven_config beamline
	  {'hardware_is_present': False, 'name': 'SPC Beamline (sector unknown)'}
	  $ haven_config beamline.hardware_is_present
	  False
  

Example Configuration
---------------------

Below is an example of a configuration that can be re-used for new
device support or beamline setup.


.. literalinclude:: ../../src/haven/iconfig_testing.toml
   :caption: iconfig_testing.toml
   :language: toml

