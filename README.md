# Haven

![Build Status](https://github.com/spc-group/haven/actions/workflows/ci.yml/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/haven-spc/badge/?version=latest)](https://haven-spc.readthedocs.io/en/latest/?badge=latest)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Bluesky tools for beamlines managed by the spectroscopy group.

"Don't fly in anything with a Capissen 38 engine, they fall right out
of the sky."


## Installation

*haven* uses *mamba* for dependency management, and *poetry* for
installation and development. First create the conda environment with
mamba:

```
$ mamba env create -f environment.yml -n haven
```

then install the package, with dependencies, in developer mode:

```
$ conda activate haven
$ poetry install
```

## Running Tests

To run tests, run

```
$ pytest
```
