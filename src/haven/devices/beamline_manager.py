from collections.abc import Mapping
from typing import Any

from apsbss.apsbss_ophyd import EpicsBssDevice, EpicsEsafDevice, EpicsProposalDevice
from ophyd import Component as Cpt
from ophyd import Device
from ophyd import DynamicDeviceComponent as DCpt
from ophyd import EpicsSignal, EpicsSignalRO


class BSSEsaf(EpicsEsafDevice):
    user_PIs = Cpt(EpicsSignal, "userPIs", string=True)
    start_timestamp = Cpt(EpicsSignal, "startTimestamp")
    end_timestamp = Cpt(EpicsSignal, "endTimestamp")


class BSSProposal(EpicsProposalDevice):
    user_PIs = Cpt(EpicsSignal, "userPIs", string=True)
    mail_in_flag = Cpt(EpicsSignal, "mailInFlag", string=False)
    proprietary_flag = Cpt(EpicsSignal, "proprietaryFlag", string=False)
    start_timestamp = Cpt(EpicsSignal, "startTimestamp")
    end_timestamp = Cpt(EpicsSignal, "endTimestamp")


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
    restart_ioc = Cpt(EpicsSignal, "restart", kind="omitted")


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

    bss = Cpt(BSS, "bss:", name="bss")
    local_storage = Cpt(LocalStorage, "local_storage:", name="local_storage")

    def __new__(
        cls: type,
        prefix: str,
        name: str,
        iocs: Mapping[str, Any] = {},
        **kwargs,
    ):
        defn: Mapping[str, tuple] = {
            key: (IOCManager, val, {}) for key, val in iocs.items()
        }
        comps = {
            "iocs": DCpt(defn),
        }
        new_cls = type("BeamlineManager", (cls,), comps)
        return object.__new__(new_cls)

    def __init__(
        self,
        prefix: str,
        name: str,
        iocs: Mapping = {},
        labels: set = {"beamline_manager"},
        **kwargs,
    ):
        super().__init__(prefix=prefix, name=name, labels=labels, **kwargs)
