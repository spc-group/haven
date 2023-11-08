from typing import Optional, Sequence
import logging
import warnings
from itertools import chain
from typing import Sequence

from ophyd import ophydobj
from ophydregistry import Registry as InstrumentRegistry
from ophydregistry.exceptions import (
    ComponentNotFound,
    MultipleComponentsFound,
    InvalidComponentLabel,
)

log = logging.getLogger(__name__)


__all__ = ["InstrumentRegistry", "registry"]


registry = InstrumentRegistry(auto_register=False)
