# Haven

![Build Status](https://github.com/spc-group/haven/actions/workflows/ci.yml/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/haven-spc/badge/?version=latest)](https://haven-spc.readthedocs.io/en/latest/?badge=latest)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Bluesky tools for beamlines managed by the spectroscopy group.

"Don't fly in anything with a Capissen 38 engine, they fall right out
of the sky."


## Setup and Installation

First, download the package from github:

```bash
$ git clone https://github.com/spc-group/haven.git
$ cd haven
```

Haven uses **pixi** for managing **environments** and **dependencies**,
and running **tasks**.

If **pixi** is not installed, follow the instructions [here](https://pixi.sh/latest/installation/).

## Configuration

Haven uses configuration files for most of the instrument-specific
details (PV prefixes, etc). Deciding which configuration files to use
is handled by Pixi. Each instrument has a Pixi feature with
environmental variables that point to the correct configuration files
to use. See ``pixi.toml`` for existing examples.


## Usage

To start an iPython session with all the instrument features loaded, use:

```bash
$ pixi run ipython
```

The default environment does not connect to any real hardware, and is
meant for demonstration purposes.

To **select a real beamline**, provide an environment using ``-e <beamline>`` or
``--environment <beamline>``:

```bash
pixi run ipython -e 25idc
```

## Firefly (GUI)

Firefly is a user-facing application for controlling the beamlines
managed by the spectroscopy group. It can be started using:

```bash
$ pixi run firefly
```

Firefly uses the same pixi environments described above.

To make changes to the window layouts using Qt Designer, use:

```bash
$ pixi run designer
```

## Bluesky Queueserver

A bluesky queueserver instance can be launched using

```shell
$ pixi run qserver
```

The specifics of the queueserver are determined by environmental
variables in the instrument-specific Pixi features (``pixi.toml``).

## Tiled API

Haven's default run-engine configuration requires a Tiled instance for
writing data. A Tiled server can be started using

```
$ pixi run tiled
```

Configuration is handled by the configuration file referenced by the
``$TILED_CONFIG`` in ``pixi.toml``.

## Running Tests

To run tests for a specific package, use:

```
$ pixi run test-haven
$ pixi run test-firefly
```

To run all tests as well as linting and type-checking, use:

```
$ pixi run test-all
```

## Building Documentation

Documentation is stored in ``docs/`` and built using Sphinx:

```
$ pixi run make-docs
```


# Packaging

Coming soon…
