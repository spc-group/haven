#!/usr/bin/env python3
from textwrap import dedent
import sys
import time
from multiprocessing import Process
from typing import Optional, List, Dict, Tuple, Any
import contextlib

import pytest
from caproto.server import PVGroup, template_arg_parser, pvproperty, run
from epics import caget, caput


class SimpleIOC(PVGroup):
    """
    An IOC with three uncoupled read/writable PVs

    Scalar PVs
    ----------
    A (int)
    B (float)

    Vectors PVs
    -----------
    C (vector of int)
    """

    A = pvproperty(value=1, doc="An integer")
    B = pvproperty(value=2.0, doc="A float")
    C = pvproperty(value=[1, 2, 3], doc="An array of integers")


@pytest.fixture
def ioc_simple():
    with simulated_ioc(SimpleIOC, prefix="simple:") as pvdb:
        yield pvdb


class VortexIOC(PVGroup):
    """
    An IOC with three uncoupled read/writable PVs

    Scalar PVs
    ----------
    A (int)
    B (float)

    Vectors PVs
    -----------
    C (vector of int)
    """

    NumImages = pvproperty(value=1, doc="Number of images to capture total.")
    TriggerMode = pvproperty(value=1, doc="Operation mode for triggering the detector")
    Acquire = pvproperty(value=0, doc="Acquire the data")
    Erase = pvproperty(
        value=0, doc="Erases the data in preparation for collecting new data"
    )


@pytest.fixture
def ioc_vortex():
    with simulated_ioc(VortexIOC, prefix="xspress:") as pvdb:
        yield pvdb


@contextlib.contextmanager
def simulated_ioc(IOC, prefix):
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=prefix, argv=[], desc=dedent(IOC.__doc__)
    )
    ioc = IOC(**ioc_options)
    # Prepare the multiprocessing
    process = Process(target=run, kwargs=dict(pvdb=ioc.pvdb, **run_options))
    process.start()
    # Drop into the calling code to run the tests
    yield ioc.pvdb
    # Stop the process now that the test is done
    process.terminate()


def ioc_arg_parser(
    *,
    desc: str,
    default_prefix: str,
    argv: Optional[List[str]] = None,
    macros: Optional[Dict[str, str]] = None,
    supported_async_libs: Optional[List[str]] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """A reusable ArgumentParser for basic example IOCs.

    Copied from caproto.server and adjusted to accept *argv* properly.

    Parameters
    ----------
    description : string
        Human-friendly description of what that IOC does
    default_prefix : string
    args : list, optional
        Defaults to sys.argv
    macros : dict, optional
        Maps macro names to default value (string) or None (indicating that
        this macro parameter is required).
    supported_async_libs : list, optional
        "White list" of supported server implementations. The first one will
        be the default. If None specified, the parser will accept all of the
        (hard-coded) choices.
    Returns
    -------
    ioc_options : dict
        kwargs to be handed into the IOC init.
    run_options : dict
        kwargs to be handed to run

    """
    parser, split_args = template_arg_parser(
        desc=desc,
        default_prefix=default_prefix,
        argv=argv,
        macros=macros,
        supported_async_libs=supported_async_libs,
    )
    return split_args(parser.parse_args(argv))


def test_simulated_ioc(ioc_simple):
    assert caget("simple:B") == 2.0
    caput("simple:A", 5)
    assert caget("simple:A") == 5
