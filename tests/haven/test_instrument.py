from pathlib import Path

from haven.devices import Motor
from haven.instrument import make_devices

haven_dir = Path(__file__).parent.parent.parent.resolve() / "src" / "haven"
toml_file = haven_dir / "iconfig_testing.toml"


def test_make_devices():
    m1, m2 = make_devices(Motor)(
        m1="255idzVME:m1",
        m2="255idzVME:m2",
    )
    assert m1.name == "m1"
    assert m1.user_readback.source == "ca://255idzVME:m1.RBV"
    assert m2.name == "m2"
    assert m2.user_readback.source == "ca://255idzVME:m2.RBV"
