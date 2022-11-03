#!/usr/bin/env python3
import os
import signal
import logging
from textwrap import dedent
import sys
import time
from multiprocessing import Process
from subprocess import Popen, PIPE
from typing import Optional, List, Dict, Tuple, Any
import contextlib
import importlib
from pathlib import Path

from tqdm import tqdm
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
from epics import caget, caput, camonitor

from . import exceptions


log = logging.getLogger(__name__)


locks = {
    "caproto": 'unlocked',
}


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


class IOC(PVGroup):
    @classmethod
    def parse_args(Cls) -> Tuple[dict, dict]:
        ioc_options, run_options = ioc_arg_parser(
            default_prefix=Cls.default_prefix,
            argv=[],
            desc=dedent(Cls.__doc__))
        ioc = Cls(**ioc_options)
        run_options["log_pv_names"] = True
        return ioc.pvdb, run_options


def wait_for_ioc(pvdb, timeout=20):
    """Block until all the PVs in the IOC have loaded."""
    # Build a list of PVs and PV fields
    all_fields = []
    fields_found = []
    for pv_name, prop in pvdb.items():
        all_fields.append(pv_name)
        # for field in prop.fields:
        #     pv = f"{pv_name}.{field}"
        #     all_fields.append(pv)
    # Wait until all the PVs have responded
    start_time = time.time()
    deadline = start_time + timeout
    all_done = False
    pbar = tqdm(total=len(all_fields), desc="Loading IOC")
    field_times = {}
    while not all_done:
        fields_left = [f for f in all_fields if f not in fields_found]
        all_done = len(fields_left) == 0
        for field in fields_left:
            val = caget(field, timeout=0.5)
            if val is not None:
                fields_found.append(field)
                pbar.update(1)
                field_times[field] = time.time() - start_time
            # Check for exceeding the timeout
            if time.time() > deadline:
                msg = f"IOC ({pvdb.keys()[0]}) did not start within {timeout} seconds. Missing: {fields_left}"
                pbar.close()
                raise exceptions.IOCTimeout(msg)
        time.sleep(0.1)
    log.debug(f"wait_for_ioc() took {time.time() - start_time:.2f} sec.")
    pbar.close()


def run_ioc(pvdb, **kwargs):
    return run(pvdb=pvdb, **kwargs)


# def simulated_ioc(IOCs, prefixes=[], fp=""):
@contextlib.contextmanager
def simulated_ioc(fp):
    # Determine name of the IOC from filename
    fp = Path(fp)
    name = fp.stem
    # Wait for all the other IOC's to be done
    # if locks['caproto'] != "unlocked":
    #     msg = f"{name} IOC could not start (locked by {locks['caproto']})."
    #     raise exceptions.IOCTimeout(msg)
        # assert False
        # log.debug("Waiting on caproto server lock.")
    # timeout = 20
    # start_time = time.time()
    # deadline = start_time + timeout
    # while locks['caproto'] != "unlocked":
    #     time.sleep(0.1)
    #     if time.time() > deadline:
    #         msg = f"{name} IOC not started within {timeout} seconds (locked by {locks['caproto']})."
    #         raise exceptions.IOCTimeout(msg)
    # log.debug(f"waiting for lock took {time.time() - start_time:.2f} seconds.")        
    locks['caproto'] = name
    # full_pvdb = {}
    # full_run_options = {}
    # for IOC, prefix in zip(IOCs, prefixes):
    #     ioc_options, run_options = ioc_arg_parser(
    #         default_prefix=prefix, argv=[], desc=dedent(IOC.__doc__),
    #     )
    #     ioc = IOC(**ioc_options)
    #     full_pvdb.update(**ioc.pvdb)
    #     full_run_options.update(**run_options)
    # Prepare the multiprocessing
    # full_run_options["log_pv_names"] = False
    # full_run_options["module_name"] = "caproto.curio.server"
    # process = Process(target=run_ioc, kwargs=dict(pvdb=full_pvdb, **full_run_options), daemon=True)
    # process.start()
    process = Popen(["python", str(fp.resolve())], stdout=PIPE, stderr=PIPE, text=True)
    # Build the pv database
    spec = importlib.util.spec_from_file_location("ioc", str(fp))
    ioc_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ioc_mod)
    pvdb, _ = ioc_mod.IOC.parse_args()
    # Wait for the ioc to load
    wait_for_ioc(pvdb=pvdb)
    # Drop into the calling code to run the tests
    yield pvdb
    # Stop the process now that the test is done
    start_time = time.time()
    os.kill(process.pid, signal.SIGINT)
    kill_start = time.time()
    timeout = 20
    stdout, stderr = process.communicate()
    print(stdout)
    print(stderr)
    # process.join(timeout=timeout)
    # while process.is_alive():
    #     if time.time() - kill_start > timeout:
    #         raise exceptions.IOCTimeout(f"{IOC} not stopped within {timeout} seconds.")
    #     time.sleep(0.1)
    # process.kill()
    # time.sleep(0.1)
    # process.close()
    locks['caproto'] = "unlocked"
    log.debug(f"Shutting down took {time.time() - start_time:.2f} sec.")        


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
    argv : list, optional
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
