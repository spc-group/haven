import re
from typing import Callable, Union

from ophyd import Component, K

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
            The instance to extract the prefix to maybe append to the
            suffix from.

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
        print(f"{kw}: {suffix} -> {new_val}")
        try:
            new_val = re.sub(self.pattern, self.repl, new_val)
        except TypeError:
            pass
        print(f"{kw}: {suffix} -> {new_val}")
        return new_val

