import logging
import sys
from logging.config import dictConfig

from .iconfig import LoggingConfig

try:
    from IPython import get_ipython

    is_ipython = get_ipython() is not None
except ImportError:
    is_ipython = False


class ColorfulFormatter(logging.Formatter):
    """Formats logs in color according to their severity."""

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    COLORS = {
        logging.DEBUG: grey,
        logging.INFO: grey,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red,
    }

    def format(self, record):
        s = super().format(record)
        s = f"{self.COLORS[record.levelno]}{s}{self.reset}"
        return s


def setup_logging(config: LoggingConfig):
    """Configure logging for a python session.

    1. Sets up logging, *config* should be a format consistent with
       `logging.config.dictConfig`.
    2. Configure CPython (and IPython) to implicitly log unhandled
       exceptions.

    """
    old_excepthook = sys.excepthook

    def log_exception_python(type, value, traceback):
        log = logging.getLogger("exceptions")
        log.exception(value)
        old_excepthook(type, value, traceback)

    def log_exception_ipython(self, etype, value, tb, tb_offset=None):
        log = logging.getLogger("exceptions")
        log.exception(value)
        self.showtraceback((etype, value, tb), tb_offset=tb_offset)

    # Ipython clobbers sys.excepthook and uses its own mechanism
    if is_ipython:
        get_ipython().set_custom_exc((Exception,), log_exception_ipython)
    else:
        sys.excepthook = log_exception_python

    dictConfig(config.model_dump(by_alias=True))
