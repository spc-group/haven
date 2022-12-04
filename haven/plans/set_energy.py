from bluesky import plan_stubs as bps

from ..instrument.instrument_registry import registry


def set_energy(mono_energy, id_energy=None):
    """All energies in eV."""
    energy = registry.find(name="energy")
    if id_energy is None:
        # Move them together to the same energy
        yield from bps.mv(energy, mono_energy)
    else:
        # Move them separately to different energies
        yield from bps.mv(
            energy.mono_energy, mono_energy, energy.id_energy, id_energy / 1000
        )
