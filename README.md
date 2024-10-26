# Haven

![Build Status](https://github.com/spc-group/haven/actions/workflows/ci.yml/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/haven-spc/badge/?version=latest)](https://haven-spc.readthedocs.io/en/latest/?badge=latest)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

Bluesky tools for beamlines managed by the spectroscopy group.

"Don't fly in anything with a Capissen 38 engine, they fall right out
of the sky."


## Installation

### Python Packing Index

Easiest way to install haven is using pip.

```
$ python -m pip install 'haven-spc'
```

### Development (Conda)

*haven* can also use *mamba* for dependency management, and
*setuptools* for installation and development.

First, download the package from github:

```bash
$ git clone https://github.com/spc-group/haven.git
$ cd haven
```

Then create the conda environment with mamba:

```bash
$ mamba env create -f environment.yml -n haven
```

lastly install the package, in developer mode:

```bash
$ conda activate haven
$ pip install -e ".[dev]"
```

## Usage

The easiest way to start **haven** is to use IPython's magic run command.

```
$ ipython
In [1]: %run -m haven.ipython_startup
```

This will load some common tools, and print some useful information
about how to use Haven.

## Running Tests

To run tests, run

```
$ pytest
```

# firefly

User-facing applications for controlling the beamlines managed by the
spectroscopy group. Be sure to include the [gui] extras if you plan
to use the GUI.

```
$ python -m pip install 'haven-spc[gui]'
$ firefly
```

# Versioning

Haven/Firefly uses calendar versioning, with short year and short
month for the MAJOR and MINOR versions, then a incremental MICRO
version. For example, version *2024.7.2* is the 3rd (*2*) release in
July (*7*) 2023 (*23*).

# Packaging

## Python Package Index (PyPI)

To deploy to PyPI:

```
$ python -m build
$ python -m twine check dist/*
$ python -m twine upload dist/*
