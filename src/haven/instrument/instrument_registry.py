import logging

from ophydregistry import Registry as InstrumentRegistry

log = logging.getLogger(__name__)


__all__ = ["InstrumentRegistry", "registry"]


registry = InstrumentRegistry(auto_register=False)
