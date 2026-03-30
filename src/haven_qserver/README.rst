Queueserver Configuration
=========================

Configuration and setup for running a bluesky-queueserver and related
tools (e.g. redis)

Full setup of the spectroscopy group's queueserver stack involves the
following parts

- **redis:** In-memory database holding queueserver history.
- **queueserver:** Runs the bluesky plans.

The command ``haven_config`` is used in several places to retrieve
configuration from a single .toml file. For non-Haven deployment,
replace `haven_config <key>` with the appropriate values.

Systemd Units
-------------

Starting and stopping these services is done through systemd
units.

1. Copy the contents of ``systemd-units`` into ``~/.config/systemd/user/``
2. Modify the units as described in the sections below.
3. Reload the modified unit files: ``systemctl --user daemon-reload``
4. [Optional] View console output of all services: ``journalctl -xef --user``
5. [Optional] View console output of a specific unit (e.g. redis): ``journalctl -xef --user --unit=redis.service``

A useful pattern is to set environmental variables in each systemd
unit file, and read these environmental variables in the various
python and shell scripts. This allows, for example, multiple
queueserver instances to be run with different ZMQ ports.

The systemd unit files **assume** the various bluesky tools are
installed in a micromamba environment named *haven*, and that this
repository is cloned to ``~/src/queueserver``. **Modify the systemd
unit files to use the correct environment and repository location.**

The systemd unit files are also capable of **setting PVs based on the
service's state**. For example, by uncommenting the lines
``ExecStopPost=...`` and ``ExecStartPost=`` in each systemd unit file,
EPICS PVs can be toggled when the units start and stop, possibly
alerting staff or users that the queueserver pipeline is not
functioning.

Multiple QueueServers
---------------------

It is possible to have multiple queueservers running, for example if
multiple branches are operating at a single beamline. In this case,
independent instances of queueserver will be started and will need
unique zeroMQ ports. These ports will be set in ``queueserver.sh`` and
so that file should be modified as needed to read ZMQ ports from
config files or environmental variables. Multiple copies of the
systemd unit (``queueserver.service``) should be made with the
correspoding environmental variables.

Redis
-----

Redis should be installed by AES-IT on the target system. The
system-wide systemd unit will not be used since it requires root
access to start and stop. No modification of the systemd unit-file is
necessary.

Queueserver
-----------

1. Install haven in a micromamba environment.
2. Modify ``.config/systemd/user/queueserver.service`` to use the
   correct conda environment, and point to the location of this repo
   and the correct bluesky directory (if needed).
