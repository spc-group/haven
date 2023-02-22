from apstools.synApps.db_2slit import Optics2Slit2D_HV

from .._iconfig import load_config
from .instrument_registry import registry


def load_slits(config=None):
    if config is None:
        config = load_config()
    # Create slits
    for name, slit_config in config['slits'].items():
        dev = Optics2Slit2D_HV(prefix=slit_config['prefix'], name=name,
                               labels={"slits"})
        registry.register(dev)
