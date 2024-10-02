#########################
Instrument Configuration
#########################

.. contents:: Table of Contents
    :depth: 3

Motivation
----------

Haven's goal is to **provide support for all of the spectroscopy
beamlines**. However, each beamline is different, and these
differences are **managed by a set of configuration files**, similar
to the .ini files used in the old LabView solution. To keep the
complexity of these configuration files manageable, Haven gets much of
the needed information from the IOCs directly.

The job of processing the configuration files is handled by the
:py:class:`~haven.instrument.Instrument` class. 

Haven/Firefly should always load without a specific configuration
file, but will probably not do anything useful.

Checking Configuration
----------------------

If Haven is installed with pip, the command ``haven_config`` can be
used to read configuration variables as they will be seen by Haven:

.. code:: bash

	  $ haven_config beamline
	  {'is_connected': False, 'name': 'SPC Beamline (sector unknown)'}
	  $ haven_config beamline.is_connected
	  False


Configuration File Priority
---------------------------

There are several sources of configuration files, described in detail
below. They are loaded in the following order, with lower numbers
taking precedence over higher numbers.

1. Files listed in the ``$HAVEN_CONFIG_FILES``
2. ``~/bluesky/instrument/iconfig.toml`` (for backwards compatibility)
3. ``~/bluesky/iconfig.toml`` (best place)
4. ``iconfig_default.toml`` packaged with Haven

Unless there's a good reason to do otherwise, **most beamline
configuration belongs in ~/bluesky/iconfig.toml**.

For example, to enable support for our Universal Robotics robot
*Austin* to 25-ID-C, open the file ``~/bluesky/iconfig.toml`` and add
the following:

.. code:: toml
   
   [robot.Austin]
   prefix = "25idAustin"

.. note::

   The prevent accidental changes, the bluesky configuration files may
   not be writable by the user accounts at the beamline. For example,
   at 25-ID, the user account does not have permission to write to
   ``~/bluesky/iconfig.toml`` so **changes must be made as the staff
   account**.
   
``HAVEN_CONFIG_FILES`` Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the environmental variable ``HAVEN_CONFIG_FILES`` is set to a
*comma-separated* list of file path, then these files will take
priority, with later entries superseding earlier entries.


``~/bluesky/iconfig.toml``
^^^^^^^^^^^^^^^^^^^^^^^^^^

The file ``~/bluesky/iconfig.toml`` will be read if it is
present. **This is the best place to put beamline-specific
configuration.**

The file ``~/bluesky/instrument/iconfig.toml`` is also read for
backwards compatibility. It should not be used for new deployments,
and support for it may be removed without warning.

``iconfig_default.toml``
^^^^^^^^^^^^^^^^^^^^^^^^

Haven includes an set of default configuration values in
``src/haven/iconfig_default.toml``. This is mainly so that Haven and
Firefly can still run during development without a dedicated
configuration file. It also serves as a starting point for deploying
Haven to a new beamline. See the section on testing below for
suggestions on how to add default configuration.

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

Example Configuration
---------------------

Below are some examples of configuration that can be re-used for new
devices support or beamline setup.

.. literalinclude:: ../../src/haven/iconfig_default.toml
   :caption: iconfig_default.toml
   :language: toml

.. literalinclude:: ../../src/haven/iconfig_testing.toml
   :caption: iconfig_testing.toml
   :language: toml

