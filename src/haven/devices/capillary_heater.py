from .ptc10 import PTC10Controller, PTC10OutputChannel, PTC10ThermocoupleChannel


class CapillaryHeater(PTC10Controller):
    def __init__(self, prefix: str, *, name: str = ""):
        with self.add_children_as_readables():
            self.output = PTC10OutputChannel(f"{prefix}5A:")
            self.thermocouple = PTC10ThermocoupleChannel(f"{prefix}2A:")
        super().__init__(prefix=prefix, name=name)
