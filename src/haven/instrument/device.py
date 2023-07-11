import re
import time as ttime
from typing import Callable, Union
import asyncio

from ophyd import Component, K


async def await_for_connection(dev, all_signals=False, timeout=2.0):
    """Wait for signals to connect

    Parameters
    ----------
    all_signals : bool, optional
        Wait for all signals to connect (including lazy ones)
    timeout : float or None
        Overall timeout
    """
    signals = [walk.item for walk in dev.walk_signals(include_lazy=all_signals)]

    pending_funcs = {
        dev: getattr(dev, "_required_for_connection", {})
        for name, dev in dev.walk_subdevices(include_lazy=all_signals)
    }
    pending_funcs[dev] = dev._required_for_connection

    t0 = ttime.time()
    while timeout is None or (ttime.time() - t0) < timeout:
        connected = all(sig.connected for sig in signals)
        if connected and not any(pending_funcs.values()):
            return
        await asyncio.sleep(min((0.05, timeout / 10.0)))

    def get_name(sig):
        sig_name = f"{dev.name}.{sig.dotted_name}"
        return f"{sig_name} ({sig.pvname})" if hasattr(sig, "pvname") else sig_name

    reasons = []
    unconnected = ", ".join(get_name(sig) for sig in signals if not sig.connected)
    if unconnected:
        reasons.append(f"Failed to connect to all signals: {unconnected}")
    if any(pending_funcs.values()):
        pending = ", ".join(
            description.format(device=dev)
            for dev, funcs in pending_funcs.items()
            for obj, description in funcs.items()
        )
        reasons.append(f"Pending operations: {pending}")
    raise TimeoutError("; ".join(reasons))


class RegexComponent(Component[K]):
    """A component with regular expression matching.

    In EPICS, it is not possible to add a field to an existing record,
    e.g. adding a ``.RnXY`` field to go alongside ``mca1.RnNM`` and
    other fields in the MCA record. A common solution is to create a
    new record with an underscore instead of the dot: ``mca1_RnBH``.

    This component include these types of field-like-records as part
    of the ROI device with a ``mca1.Rn`` prefix but performing
    subsitution on the device name using regular expressions. See the
    documentation for ``re.sub`` for full details.

    Example
    =======

    ```
    class ROI(mca.ROI):
        name = RECpt(EpicsSignal, "NM", lazy=True)
        is_hinted = RECpt(EpicsSignal, "BH",
                          pattern=r"^(.+)\.R(\d+)",
                          repl=r"\1_R\2",
                          lazy=True)

    class MCA(mca.EpicsMCARecord):
        roi0 = Cpt(ROI, ".R0")
        roi1 = Cpt(ROI, ".R1")

    mca = MCA(prefix="mca")
    # *name* has the normal concatination
    assert mca.roi0.name.pvname == "mca.R0NM"
    # *is_hinted* has regex substitution
    assert mca.roi0.is_hinted.pvname == "mca_R0BH"

    ```

    """

    def __init__(self, *args, pattern: str, repl: Union[str, Callable], **kwargs):
        """*pattern* and *repl* match their use in ``re.sub``."""
        self.pattern = pattern
        self.repl = repl
        super().__init__(*args, **kwargs)

    def maybe_add_prefix(self, instance, kw, suffix):
        """Parse prefix and suffix with regex suffix if kw is in self.add_prefix.

        Parameters
        ----------
        instance : Device
            The instance from which to extract the prefix to maybe
            append to the suffix.

        kw : str
            The key of associated with the suffix.  If this key is
            self.add_prefix than prepend the prefix to the suffix and
            return, else just return the suffix.

        suffix : str
            The suffix to maybe have something prepended to.

        Returns
        -------
        str

        """
        new_val = super().maybe_add_prefix(instance, kw, suffix)
        try:
            new_val = re.sub(self.pattern, self.repl, new_val)
        except TypeError:
            pass
        return new_val