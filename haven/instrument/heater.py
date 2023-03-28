from ophyd import PVPositioner, EpicsSignalRO, EpicsSignalWithRBV, Component as Cpt
from apstools.devices import PTC10PositionerMixin, PTC10AioChannel as PTC10AioChannelBase, PTC10TcChannel


# The apstools version uses "voltage_RBV" as the PVname
class PTC10AioChannel(PTC10AioChannelBase):
    """
    SRS PTC10 AIO module
    """

    voltage = Cpt(EpicsSignalRO, "output_RBV", kind="config")


class CapillaryHeater(PTC10PositionerMixin, PVPositioner):
    readback = Cpt(EpicsSignalRO, "2A:temperature", kind="hinted")
    setpoint = Cpt(EpicsSignalWithRBV, "5A:setPoint", kind="hinted")

    pid = Cpt(PTC10AioChannel, "5A:")
    tc = Cpt(PTC10TcChannel, "2A:")
