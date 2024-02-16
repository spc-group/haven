import asyncio
import logging

from ophyd import Component as Cpt
from ophyd import DynamicDeviceComponent as DCpt
from ophyd import Device, EpicsMotor, EpicsSignal, EpicsSignalRO

from .._iconfig import load_config
from .device import aload_devices, make_device

log = logging.getLogger(__name__)

class Sample(Device):
 

    present = Cpt(EpicsSignalRO, ":present")
    empty = Cpt(EpicsSignalRO, ":empty")
    load = Cpt(EpicsSignalRO, ":load")
    unload = Cpt(EpicsSignalRO, ":unload")
    x = Cpt(EpicsSignalRO, ":x")
    y = Cpt(EpicsSignalRO, ":y")
    z = Cpt(EpicsSignalRO, ":z")
    rx = Cpt(EpicsSignalRO, ":rx")
    ry = Cpt(EpicsSignalRO, ":ry")
    rz = Cpt(EpicsSignalRO, ":rz")

def transfer_samples(num_samples: int):
    """Create a dictionary with robot sample device definitions.
    For use with an ophyd DynamicDeviceComponent.
    Parameters
    ==========
    num_dios
      How many samples to create.
    """
    samples = {}
    samples_attrs = ['present', 'empty', 'load', 'unload','x', 'y', 'z', 'rx', 'ry', 'rz']
    for n in range(num_samples):
        samples[f"sample{n}"] = (Sample, f":sample{n}", {})
        # samples[f"sample{n}_{attr}"] = (EpicsSignal, f":sample{n}:{attr}", dict(labels={"transfer"}))
    #breakpoint()
    return samples


class Robot(Device):
    # joints and position
    i = Cpt(EpicsMotor, ":i", labels={ "joints"})
    j = Cpt(EpicsMotor, ":j", labels={ "joints"})
    k = Cpt(EpicsMotor, ":k", labels={ "joints"})
    l = Cpt(EpicsMotor, ":l", labels={ "joints"})
    m = Cpt(EpicsMotor, ":m", labels={ "joints"})
    n = Cpt(EpicsMotor, ":n", labels={ "joints"})
    x = Cpt(EpicsMotor, ":x", labels={ "joints"})
    y = Cpt(EpicsMotor, ":y", labels={ "joints"})
    z = Cpt(EpicsMotor, ":z", labels={ "joints"})
    rx = Cpt(EpicsMotor, ":rx", labels={ "joints"})
    ry = Cpt(EpicsMotor, ":ry", labels={ "joints"})
    rz = Cpt(EpicsMotor, ":rz", labels={ "joints"})
    acc = Cpt(EpicsSignal, ":acceleration", labels={ "joints"}, kind="config")
    vel = Cpt(EpicsSignal, ":velocity", labels={ "joints"}, kind="config")
    
    # dashboard
    remote_control = Cpt(EpicsSignalRO, ":dashboard:remote_control", labels={"dashboard"}, kind="config")
    program = Cpt(EpicsSignal, ":dashboard:program_rbv", labels={"dashboard"}, kind="config")
    program_rbv = Cpt(EpicsSignalRO, ":dashboard:program_rbv", labels={"dashboard"}, kind="config")
    installation = Cpt(EpicsSignal, ":dashboard:installation", labels={"dashboard"}, kind="config")
    playRbt = Cpt(EpicsSignal, ":dashboard:play", labels={"dashboard"}, kind="config")
    stopRbt = Cpt(EpicsSignal, ":dashboard:stop", labels={"dashboard"}, kind="config")
    pauseRbt = Cpt(EpicsSignal, ":dashboard:pause", labels={"dashboard"}, kind="config")
    quit = Cpt(EpicsSignal, ":dashboard:quit", labels={"dashboard"}, kind="config")
    shutdown = Cpt(EpicsSignal, ":dashboard:shutdown", labels={"dashboard"}, kind="config")
    release_brake = Cpt(EpicsSignal, ":dashboard:release_brake", labels={"dashboard"}, kind="config")
    close_safety_popup = Cpt(EpicsSignal, ":dashboard:close_safety_popup", labels={"dashboard"}, kind="config")
    unlock_protective_stop = Cpt(EpicsSignal, ":dashboard:unlock_protective_stop", labels={"dashboard"}, kind="config")
    restart_safety = Cpt(EpicsSignal, ":dashboard:restart_safety", labels={"dashboard"}, kind="config")
    program_running = Cpt(EpicsSignal, ":dashboard:program_running", labels={"dashboard"}, kind="config")
    safety_status = Cpt(EpicsSignal, ":dashboard:safety_status", labels={"dashboard"}, kind="config")
    power = Cpt(EpicsSignal, ":dashboard:power", labels={"dashboard"}, kind="config")
    power_rbv = Cpt(EpicsSignalRO, ":dashboard:power_rbv", labels={"dashboard"}, kind="config")
    
    # gripper
    act = Cpt(EpicsSignal, ":gripper:ACT", labels={"gripper"}, kind="config")
    acr = Cpt(EpicsSignal, ":gripper:ACR", labels={"gripper"}, kind="config")
    cls = Cpt(EpicsSignal, ":gripper:CLS", labels={"gripper"}, kind="config")
    opn = Cpt(EpicsSignal, ":gripper:OPN", labels={"gripper"}, kind="config")
    rbv = Cpt(EpicsSignal, ":gripper:RBV", labels={"gripper"}, kind="config")
    val = Cpt(EpicsSignal, ":gripper:VAL", labels={"gripper"}, kind="config")
    
    # busy 
    busy = Cpt(EpicsSignal, ":busy", labels={"busy"}, kind="omitted")
    
    # sample transfer
    current_sample = Cpt(EpicsSignalRO, ":current_sample", labels={"transfer"}, kind="config")
    unload_current_sample = Cpt(EpicsSignal, ":unload_current_sample", labels={"transfer"}, kind="config")
    current_sample_reset = Cpt(EpicsSignal, ":current_sample_reset", labels={"transfer"}, kind="config")
    home = Cpt(EpicsSignal, ":home", labels={"transfer"}, kind="config")
    cal_stage = Cpt(EpicsSignal, ":cal_stage", labels={"transfer"}, kind="config")
    
    samples = DCpt(transfer_samples(24), kind="normal")



def load_robot_coros(config=None):
    # Load PV's from config
    if config is None:
        config = load_config()
    robots = config["robot"]
    for name, cfg in robots.items():
        yield make_device(
            Robot, name=name, labels={"robots"}, prefix=cfg['prefix']
        )


def load_robot(config=None):
    asyncio.run(aload_devices(*load_robot_coros(config=config)))


# -----------------------------------------------------------------------------
# :author:    Yanna Chen
# :email:     yannachen@anl.gov
# :copyright: Copyright © 2024, UChicago Argonne, LLC
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
