#!/usr/bin/env python3
from textwrap import dedent
import sys
import time
from multiprocessing import Process
from typing import Optional, List, Dict, Tuple, Any
import contextlib

import pytest
from caproto import ChannelType
from caproto.server import (
    PVGroup,
    template_arg_parser,
    pvproperty,
    run,
    records,
    PvpropertyDouble,
)
from epics import caget, caput


# Subclass the motor fields here. It's important to use this 'register_record'
# decorator to tell caproto where to find this record:
@records.register_record
class ResponsiveMotorFields(records.MotorFields):
    # The custom fields are identified by this string, which is overridden from
    # the superclass _record_type of 'motor':
    _record_type = 'responsive_motor'

    # To override or extend the motor fields, we have to duplicate them here:
    user_readback_value = pvproperty(name='RBV', dtype=ChannelType.DOUBLE,
                                     doc='User Readback Value', read_only=True)

    # Then we are free to extend the fields as normal pvproperties:
    @user_readback_value.scan(period=0.1)
    async def user_readback_value(self, instance, async_lib):
        setpoint = self.parent.value
        pos = setpoint
        # Set the use, dial, and then raw readbacks:
        timestamp = time.time()
        await instance.write(pos, timestamp=timestamp)
        await self.dial_readback_value.write(pos, timestamp=timestamp)
        await self.raw_readback_value.write(int(pos * 100000.),
                                            timestamp=timestamp)



@contextlib.contextmanager
def simulated_ioc(IOC, prefix):
    ioc_options, run_options = ioc_arg_parser(
        default_prefix=prefix, argv=[], desc=dedent(IOC.__doc__)
    )
    ioc = IOC(**ioc_options)
    # Prepare the multiprocessing
    process = Process(target=run, kwargs=dict(pvdb=ioc.pvdb, **run_options))
    process.start()
    time.sleep(1)
    # Drop into the calling code to run the tests
    yield ioc.pvdb
    # Stop the process now that the test is done
    process.terminate()
    while process.is_alive():
        pass
    process.close()


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
