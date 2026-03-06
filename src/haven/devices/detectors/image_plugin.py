import numpy as np
from ophyd_async.epics.adcore import NDPluginBaseIO
from ophyd_async.epics.core import epics_signal_r


class NDPluginPva(NDPluginBaseIO):
    def __init__(self, prefix: str, *args, **kwargs):
        # Add a PVA signal instead of CA
        prefix_ = prefix
        if prefix_.startswith("ca://"):
            prefix_ = prefix_.lstrip("ca://")
        pv_path = f"pva://{prefix_.replace('ca://', 'pva://')}Image"
        self.image = epics_signal_r(np.ndarray, pv_path)
        super().__init__(prefix, *args, **kwargs)
