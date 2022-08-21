import logging
import warnings
import unicodedata
import re
import datetime as dt
from pathlib import Path
from typing import Sequence, Optional, Union

import pytz
from bluesky.callbacks import CallbackBase

from . import exceptions


log = logging.getLogger(__name__)


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^/.\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


class XDIWriter(CallbackBase):
    """A callback class for bluesky that will save data to an XDI file.

    The XAFS data interchange (XDI) format is a plain text,
    tab-separated file format that standardizes XAFS data. Metadata is
    also included in headers.

    The location of the file is determined by passing the *filename*
    parameter in when created the writer object:

    .. code-block:: python

      writer = XDIWriter(fd="./my_experiment.xdi")

    Placeholders can be included that will be filled-in with metadata
    during the start phase of the plan, for example:

    .. code-block:: python

      plan = energy_scan(..., E0="Ni_K", md=dict(sample_name="nickel oxide"))
      writer_callback = XDIWriter(fd="./{year}{month}{day}_{sample_name}_{edge}.xdi")
      RE(plan, writer)

    Assuming the date is 2022-08-19, then the filename will become
    "20220819_nickel-oxide_Ni_K.xdi".

    *{year}*, *{month}*, *{day}* describe the numerical, zero-padded
    year, month and day when the callback handles the start document
    for the plan. The remaining fields in the start document are also
    available, and will likely vary from plan to plan. Either consult
    the documentation for the plan being executed, or inspect the logs
    for the dictionary metadata at level logging.INFO when using an
    invalid placeholder.

    Parameters
    ==========
    fd
      Either an open file with write intent, or a Path or string with
      the file location. If *fd* is not already an open file, it will
      be created when the ``start()`` method is called.

    """

    _fd = None
    fp: Optional[Union[str, Path]] = None
    column_names: Sequence[str] = []
    start_time: dt.datetime = None

    def __init__(self, fd, *args, **kwargs):
        is_file_obj = hasattr(fd, "writable")
        if is_file_obj:
            # *fd* is an open file object
            # Make sure it is writable
            if fd.writable():
                log.debug(f"Found open, writable file: {fd}")
                self._fd = fd
            else:
                msg = f"No write intent on file: {fd}"
                log.error(msg)
                raise exceptions.FileNotWritable(msg)
        else:
            # Assume *fd* is a path to a file
            self.fp = Path(fd)
        return super().__init__(*args, **kwargs)

    @property
    def fd(self):
        """Retrieve the open writable file object for this writer."""
        if self._fd is None:
            log.debug(f"Opening file: {self.fp.resolve()}")
            self._fd = open(self.fp, mode="x")
        return self._fd

    # def __call__(self, name, doc):
    #     from pprint import pprint as print
    #     print(f"{name}: {doc}")
    #     return super().__call__(name, doc)

    def _path_metadata(self, doc={}):
        """Prepare the metadata for string formatting the output file path."""
        md = {
            "year": self.start_time.strftime("%Y"),
            "month": self.start_time.strftime("%m"),
            "day": self.start_time.strftime("%d"),
        }
        md.update(doc)
        return md

    def start(self, doc):
        self.start_time = dt.datetime.now().astimezone()
        # Format the file name based on metadata
        if self.fp is not None:
            fp = str(self.fp)
            md = self._path_metadata(doc=doc)
            try:
                fp = fp.format(**md)
            except KeyError as e:
                msg = f"Could not find match key {e} in {fp}."
                log.error(msg)
                log.info(f"Metadata is: {md}")
                raise exceptions.XDIFilenameKeyNotFound(msg) from None
            fp = slugify(fp)
            self.fp = Path(fp)
        fd = self.fd
        # Write package version information
        versions = ["XDI/1.0"]
        versions += [f"{name}/{ver}" for name, ver in doc.get("versions", {}).items()]
        fd.write(f"# {' '.join(versions)}\n")
        # Column names
        detectors = doc.get("detectors", [])
        motors = doc.get("motors", [])
        motors = sorted(
            motors, key=lambda s: s != "energy"
        )  # Put energy in the first column
        self.column_names = motors + detectors + ["time"]
        columns = [
            f"# Column.{num+1}: {name}\n" for num, name in enumerate(self.column_names)
        ]

        fd.write("".join(columns))
        # X-ray edge information
        edge_str = doc.get("edge", None)
        try:
            elem, edge = edge_str.split("_")
        except (AttributeError, ValueError):
            msg = f"Could not parse X-ray edge metadata: {edge_str}"
            warnings.warn(msg)
            log.warning(msg)
        else:
            fd.write(f"# Element.symbol: {elem}\n")
            fd.write(f"# Element.edge: {edge}\n")
        now = self.start_time
        fd.write(f"# Scan.start_time: {now.strftime('%Y-%m-%d %H:%M:%S%z')}\n")
        md_paths = [
            "facility.name",
            "facility.xray_source",
            "beamline.name",
            "beamline.pv_prefix",
        ]
        for path in md_paths:
            val = doc
            try:
                for piece in path.split("."):
                    val = val[piece]
                fd.write(f"# {path}: {val}\n")
            except KeyError:
                continue

    def event(self, doc):
        """Save the data in tab-separated value, in order of
        ``self.column_names``.

        """
        data = doc["data"]
        fd = self.fd
        values = []
        for col in self.column_names:
            if col == "time":
                values.append(str(doc["time"]))
            else:
                values.append(str(data[col]))
        line = "\t".join(values)
        fd.write(line)
