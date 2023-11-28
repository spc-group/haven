#!/usr/bin/env python3
import contextlib
import importlib
import logging
import os
import signal
import time
from pathlib import Path
from subprocess import PIPE, Popen
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple

from caproto import ChannelType
from caproto.server import PVGroup, pvproperty, records, run, template_arg_parser
from epics import caget
from tqdm import tqdm

from . import exceptions

log = logging.getLogger(__name__)


locks = {
    "caproto": "unlocked",
}


# Subclass the motor fields here. It's important to use this 'register_record'
# decorator to tell caproto where to find this record:
@records.register_record
class ResponsiveMotorFields(records.MotorFields):
    # The custom fields are identified by this string, which is overridden from
    # the superclass _record_type of 'motor':
    _record_type = "responsive_motor"

    # To override or extend the motor fields, we have to duplicate them here:
    user_readback_value = pvproperty(
        name="RBV", dtype=ChannelType.DOUBLE, doc="User Readback Value", read_only=True
    )

    # Then we are free to extend the fields as normal pvproperties:
    @user_readback_value.scan(period=0.1)
    async def user_readback_value(self, instance, async_lib):
        setpoint = self.parent.value
        pos = setpoint
        # Set the use, dial, and then raw readbacks:
        timestamp = time.time()
        await instance.write(pos, timestamp=timestamp)
        await self.dial_readback_value.write(pos, timestamp=timestamp)
        await self.raw_readback_value.write(int(pos * 100000.0), timestamp=timestamp)


class IOC(PVGroup):
    @classmethod
    def parse_args(Cls) -> Tuple[dict, dict]:
        ioc_options, run_options = ioc_arg_parser(
            default_prefix=Cls.default_prefix, argv=[], desc=dedent(str(Cls.__doc__))
        )
        ioc = Cls(**ioc_options)
        run_options["log_pv_names"] = True
        # run_options["interfaces"] = ["127.0.0.1"]
        return ioc.pvdb, run_options


def wait_for_ioc(pvdb, process=None, timeout=30):
    """Block until all the PVs in the IOC have loaded."""
    # Build a list of PVs and PV fields
    all_fields = []
    fields_found = []
    for pv_name, prop in pvdb.items():
        all_fields.append(pv_name)
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
                msg = (
                    f"IOC ({list(pvdb)[0]}) did not start within "
                    f"{timeout} seconds. Missing: {fields_left}"
                )
                if process is not None:
                    log.error(f"IOC output: {process.stdout.read()}")
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
    locks["caproto"] = name
    # Build the pv database
    spec = importlib.util.spec_from_file_location("ioc", str(fp))
    ioc_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ioc_mod)
    pvdb, _ = ioc_mod.IOC.parse_args()
    # Make sure the IOC is not already running
    test_pv = list(pvdb.keys())[0]
    response = caget(test_pv, timeout=1.0, connection_timeout=1.0)
    if response is None:
        # IOC is not running, so start it
        process = Popen(
            ["python", str(fp.resolve())], stdout=PIPE, stderr=PIPE, text=True
        )
    else:
        process = None
        log.warning(f"IOC already running: {test_pv} = {response}")
    # Wait for the ioc to load
    wait_for_ioc(pvdb=pvdb, process=process)
    # Drop into the calling code to run the tests
    yield pvdb
    # Stop the process now that the test is done
    if process is not None:
        start_time = time.time()
        os.kill(process.pid, signal.SIGINT)
        stdout, stderr = process.communicate()
        # print(stdout)
        # print(stderr)
        locks["caproto"] = "unlocked"
        log.debug(f"Shutting down took {time.time() - start_time:.2f} sec.")


def ioc_arg_parser(
    *,
    desc: str,
    default_prefix: str,
    argv: Optional[List[str]] = None,
    macros: Optional[Dict[str, str]] = None,
    supported_async_libs: Optional[List[str]] = None,
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


# -----------------------------------------------------------------------------
# :author:    Mark Wolfman
# :email:     wolfman@anl.gov
# :copyright: Copyright © 2023, UChicago Argonne, LLC
#
# Distributed under the terms of the 3-Clause BSD License
#
# The full license is in the file LICENSE, distributed with this software.
#
# DISCLAIMER
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# -----------------------------------------------------------------------------
