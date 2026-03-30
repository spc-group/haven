Environment & Configuration
===========================

This how-to guide covers configuring a python environment to run
Haven, Firefly, and the Haven Queueserver.

Haven uses Pixi for managing instrument configurations. For standard
deployment, these variables are set in the pixi.toml file. Adding a
new instrument requires the following steps:

1. clone the Haven repository as the beamline service account
   (e.g. ``s255idzuser``): ``git clone
   https://github.com/spc-group/haven.git``
2. Add a section of environmental variables to ``pixi.toml`` (see the
   example below)
3. Create the configuration files pointed to by the environmental
   variables

Environmental Variables
-----------------------

Each instrument should have a Pixi feature that sets the appropriate
environmental variables to operate that beamline:

.. code-block:: toml

    [feature.255idz.activation.env]
    BLUESKY_DIR = "/net/s255data/xorApps/bluesky/255idz/"
    HAVEN_CONFIG_FILES = "${BLUESKY_DIR}iconfig.toml"
    TILED_CONFIG = "${BLUESKY_DIR}/.tiled_server_config.yml"
    QSERVER_ZMQ_CONTROL_ADDRESS = "tcp://localhost:60617"
    QSERVER_ZMQ_CONTROL_ADDRESS_FOR_SERVER = "tcp://*:60617"
    QSERVER_ZMQ_INFO_ADDRESS = "tcp://localhost:60627"
    QSERVER_ZMQ_INFO_ADDRESS_FOR_SERVER = "tcp://*:60627"

To properly configure an environment for running Haven, Firefly, the
Queueserver, and Tiled, configure the following environmental
variables:

``BLUESKY_DIR``
  Path to a folder for holding generated files from queueserver,
  Tiled, etc.
``HAVEN_CONFIG_FILES``
  Comma-separated list of paths to the local configuration files.
``TILED_CONFIG``
  Path to the file holding `Tiled server configuration`_.
``QSERVER_ZMQ_CONTROL_ADDRESS``
  The ZeroMQ host and port to be used for clients to connect to the
  queueserver. E.g. ``tcp://hostname.anl.gov:60615``
``QSERVER_ZMQ_CONTROL_ADDRESS_FOR_SERVER``
  The ZeroMQ host and port to be used by the queueserver
  itself. E.g. ``tcp://*:60615``
``QSERVER_ZMQ_INFO_ADDRESS``
  The ZeroMQ host and port to be used for clients to connect to the
  queueserver. E.g. ``tcp://hostname.anl.gov:60615``
``QSERVER_ZMQ_INFO_ADDRESS_FOR_SERVER``
  The ZeroMQ host and port to be used by the queueserver
  itself. E.g. ``tcp://*:60625``


.. _Tiled server configuration: https://blueskyproject.io/tiled/how-to/configuration.html
