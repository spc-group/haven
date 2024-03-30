import asyncio

from ophyd import Device, DynamicDeviceComponent as DCpt, Component as Cpt, EpicsSignal, EpicsSignalRO
from apsbss.apsbss_ophyd import EpicsBssDevice, EpicsEsafDevice, EpicsProposalDevice

from .device import make_device, aload_devices
from .._iconfig import load_config


class BSSEsaf(EpicsEsafDevice):
    user_PIs = Cpt(EpicsSignal, "userPIs", string=True)


class BSSProposal(EpicsProposalDevice):
    user_PIs = Cpt(EpicsSignal, "userPIs", string=True)


class BSS(EpicsBssDevice):
    esaf = Cpt(BSSEsaf, "esaf:")
    proposal = Cpt(BSSProposal, "proposal:")


class LocalStorage(Device):
    file_system = Cpt(EpicsSignal, "file_system", kind="config")
    sub_directory = Cpt(EpicsSignal, "sub_directory", kind="config")
    full_path = Cpt(EpicsSignalRO, "full_path", kind="config")
    exists = Cpt(EpicsSignalRO, "exists", kind="config")
    
    create = Cpt(EpicsSignal, "create", kind="omitted")


class IOCManager(Device):
    startable = Cpt(EpicsSignal, "startable", kind="config")
    stoppable = Cpt(EpicsSignal, "stoppable", kind="config")
    status = Cpt(EpicsSignal, "status", kind="config")
    console = Cpt(EpicsSignal, "console", kind="config")

    start_ioc = Cpt(EpicsSignal, "start", kind="omitted")
    stop_ioc = Cpt(EpicsSignal, "stop", kind="omitted")


class BeamlineManager(Device):
    """A beamline manager IOC.

    IOCs
    ----

    The beamline manager can control other IOCs. To properly set this
    up, pass a dictionary called *iocs* when initializing this object,
    which should have the IOC names as keys and the corresponding PV
    suffixes as values. This will create a dynamic device component
    *iocs* matching the IOC managers.

    """
    bss = BSS("bss:", name="bss")
    local_storage = LocalStorage("local_storage:", name="local_storage")

    def __new__(
        cls,
        prefix,
        *args,
        iocs={},
        **kwargs,
    ):
        defn = {key: (IOCManager, val, {}) for key, val in iocs.items()}
        comps = {
            "iocs": DCpt(defn),
        }
        new_cls = type("BeamlineManager", (cls,), comps)
        return object.__new__(new_cls)

    def __init__(self, *args, iocs={}, **kwargs):
        super().__init__(*args, **kwargs)
            

def load_beamline_manager_coros(config=None):
    # Load configuration for the beamline manager
    if config is None:
        config = load_config()
    try:
        cfg = config["beamline_manager"]
    except KeyError:
        return
    # Determine manager parameters from the configuration
    prefix = ""
    # Set up the beamline manager
    yield make_device(
        BeamlineManager,
        prefix=cfg['prefix'],
        name=cfg['name'],
        labels={"beamline_manager"},
    )


def load_beamline_manager(config=None):
    loop = asyncio.get_event_loop()
    return asyncio.run(aload_devices(*load_beamline_manager_coros(config=config)))
