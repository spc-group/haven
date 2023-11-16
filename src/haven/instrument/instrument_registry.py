import logging
import warnings
from itertools import chain
from typing import Optional, Sequence

from ophyd import ophydobj
from ophydregistry import Registry as InstrumentRegistry
from ophydregistry.exceptions import (
    ComponentNotFound,
    InvalidComponentLabel,
    MultipleComponentsFound,
)

log = logging.getLogger(__name__)


__all__ = ["InstrumentRegistry", "registry"]


registry = InstrumentRegistry(auto_register=False)
