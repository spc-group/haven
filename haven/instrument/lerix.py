import numpy as np
from ophyd.pseudopos import pseudo_position_argument, real_position_argument
from ophyd import PseudoPositioner, PseudoSingle, EpicsMotor
from ophyd import Component as Cpt, FormattedComponent as FCpt, Device

from .._iconfig import load_config
from .instrument_registry import registry


class RowlandPositioner(PseudoPositioner):
    def __init__(
        self,
        x_motor_pv: str,
        y_motor_pv: str,
        z_motor_pv: str,
        z1_motor_pv: str,
        *args,
        **kwargs
    ):
        self.x_motor_pv = x_motor_pv
        self.y_motor_pv = y_motor_pv
        self.z_motor_pv = z_motor_pv
        self.z1_motor_pv = z1_motor_pv
        super().__init__(*args, **kwargs)

    # Pseudo axes
    D: PseudoSingle = Cpt(PseudoSingle, name="D", limits=(0, 1000))
    theta: PseudoSingle = Cpt(PseudoSingle, name="theta", limits=(0, 180))
    alpha: PseudoSingle = Cpt(PseudoSingle, name="alpha", limits=(0, 180))

    # Real axes
    x: EpicsMotor = FCpt(EpicsMotor, "{x_motor_pv}", name="x")
    y: EpicsMotor = FCpt(EpicsMotor, "{y_motor_pv}", name="y")
    z: EpicsMotor = FCpt(EpicsMotor, "{z_motor_pv}", name="z")
    z1: EpicsMotor = FCpt(EpicsMotor, "{z1_motor_pv}", name="z1")

    @pseudo_position_argument
    def forward(self, pseudo_pos):
        """Run a forward (pseudo -> real) calculation"""
        # Convert degrees to radians
        D = pseudo_pos.D
        theta = pseudo_pos.theta / 180.0 * np.pi
        alpha = pseudo_pos.alpha / 180.0 * np.pi
        # Convert virtual positions to real positions
        x = D * (np.sin(theta + alpha)) ** 2
        y = D * ((np.sin(theta + alpha)) ** 2 - (np.sin(theta - alpha)) ** 2)
        z1 = D * np.sin(theta - alpha) * np.cos(theta + alpha)
        z2 = D * np.sin(theta - alpha) * np.cos(theta - alpha)
        z = z1 + z2
        return self.RealPosition(
            x=x,
            y=y,
            z=z,
            z1=z1,
        )

    @real_position_argument
    def inverse(self, real_pos):
        """Run an inverse (real -> pseudo) calculation"""
        return self.PseudoPosition(D=0, theta=0, alpha=0)


@registry.register
class LERIXSpectrometer(Device):
    rowland = Cpt(
        RowlandPositioner,
        x_motor_pv="vme_crate_ioc:m1",
        y_motor_pv="vme_crate_ioc:m2",
        z_motor_pv="vme_crate_ioc:m3",
        z1_motor_pv="vme_crate_ioc:m4",
        name="rowland",
    )


def load_lerix_spectrometers(config=None):
    if config is None:
        config = load_config()
    # Create spectrometers
    for name, cfg in config["lerix"].items():
        rowland = cfg["rowland"]
        # device = LERIXSpectrometer(name=name, x_motor_pv=rowland['x_motor_pv'], y_motor_pv=rowland['y_motor_pv'], z_motor_pv=rowland['z_motor_pv'], z1_motor_pv=rowland['z1_motor_pv'], labels={"lerix_spectrometers"})
        device = RowlandPositioner(
            name=name,
            x_motor_pv=rowland["x_motor_pv"],
            y_motor_pv=rowland["y_motor_pv"],
            z_motor_pv=rowland["z_motor_pv"],
            z1_motor_pv=rowland["z1_motor_pv"],
            labels={"lerix_spectrometers"},
        )
        registry.register(device)
