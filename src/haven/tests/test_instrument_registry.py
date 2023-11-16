import pytest
from ophyd import Device, EpicsMotor, sim

from haven.instrument import InstrumentRegistry
from haven.exceptions import (
    ComponentNotFound,
    MultipleComponentsFound,
)


def test_register_component():
    # Prepare registry
    reg = InstrumentRegistry(auto_register=False)
    # Create an unregistered component
    cpt = sim.SynGauss(
        "I0",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"ion_chamber"},
    )
    # Make sure the component doesn't get found without being registered
    with pytest.raises(ComponentNotFound):
        list(reg.findall(label="ion_chamber"))
    with pytest.raises(ComponentNotFound):
        list(reg.findall(name="I0"))
    # Now register the component
    cpt = reg.register(cpt)
    # Confirm that it's findable by label
    results = reg.findall(label="ion_chamber")
    assert cpt in results
    # Config that it's findable by name
    results = reg.findall(name="I0")
    assert cpt in results


def test_find_missing_components():
    """Test that registry raises an exception if no matches are found."""
    reg = InstrumentRegistry()
    cpt = sim.SynGauss(
        "I0",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"ion_chamber"},
    )
    reg.register(cpt)
    # Now make sure a different query still returns no results
    with pytest.raises(ComponentNotFound):
        reg.findall(label="spam")


def test_find_allow_missing_components():
    """Test that registry tolerates missing components with the
    *allow_none* argument.

    """
    reg = InstrumentRegistry()
    # Get some non-existent devices and check that the right nothing is returned
    assert list(reg.findall(label="spam", allow_none=True)) == []
    assert reg.find(name="eggs", allow_none=True) is None


def test_exceptions():
    reg = InstrumentRegistry()
    reg.register(Device("", name="It"))
    # Test if a non-existent labels throws an exception
    with pytest.raises(ComponentNotFound):
        reg.find(label="spam")


def test_as_class_decorator():
    reg = InstrumentRegistry()
    # Create a dummy decorated class
    IonChamber = type("IonChamber", (Device,), {})
    IonChamber = reg.register(IonChamber)
    # Instantiate the class
    IonChamber("PV_PREFIX", name="I0", labels={"ion_chamber"})
    # Check that it gets retrieved
    result = reg.find(label="ion_chamber")
    assert result.prefix == "PV_PREFIX"
    assert result.name == "I0"


def test_find_component():
    # Prepare registry
    reg = InstrumentRegistry()
    # Create an unregistered component
    cptA = sim.SynGauss(
        "I0",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"ion_chamber"},
    )
    cptB = sim.SynGauss(
        "It",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"ion_chamber"},
    )
    # Register the components
    reg.register(cptA)
    reg.register(cptB)
    # Only one match should work fine
    result = reg.find(name="I0")
    assert result is cptA
    # Multiple matches should raise an exception
    with pytest.raises(MultipleComponentsFound):
        result = reg.find(label="ion_chamber")


def test_find_name_by_dot_notation():
    # Prepare registry
    reg = InstrumentRegistry()
    # Create a simulated component
    cptA = sim.SynGauss(
        "I0",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"ion_chamber"},
    )
    reg.register(cptA)
    # Only one match should work fine
    result = reg.find(name="I0.val")
    assert result is cptA.val


def test_find_labels_by_dot_notation():
    # Prepare registry
    reg = InstrumentRegistry()
    # Create a simulated component
    cptA = sim.SynGauss(
        "I0",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"ion_chamber"},
    )
    reg.register(cptA)
    # Only one match should work fine
    result = reg.find(label="ion_chamber.val")
    assert result is cptA.val


def test_find_any():
    # Prepare registry
    reg = InstrumentRegistry()
    # Create an unregistered component
    cptA = sim.SynGauss(
        "I0",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"ion_chamber"},
    )
    cptB = sim.SynGauss(
        "It",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={"ion_chamber"},
    )
    cptC = sim.SynGauss(
        "ion_chamber",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
    )
    cptD = sim.SynGauss(
        "sample motor",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={},
    )
    # Register the components
    reg.register(cptA)
    reg.register(cptB)
    reg.register(cptC)
    reg.register(cptD)
    # Only one match should work fine
    result = reg.findall(any_of="ion_chamber")
    assert cptA in result
    assert cptB in result
    assert cptC in result
    assert cptD not in result


def test_find_by_device():
    """The registry should just return the device itself if that's what is passed."""
    # Prepare registry
    reg = InstrumentRegistry()
    # Register a component
    cptD = sim.SynGauss(
        "sample motor",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={},
    )
    reg.register(cptD)
    # Pass the device itself to the find method
    result = reg.find(cptD)
    assert result is cptD


def test_find_by_list_of_names():
    """Will the findall() method handle lists of things to look up."""
    # Prepare registry
    reg = InstrumentRegistry()
    # Register a component
    cptA = sim.SynGauss(
        "sample motor A",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={},
    )
    cptB = sim.SynGauss(
        "sample motor B",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={},
    )
    cptC = sim.SynGauss(
        "sample motor C",
        sim.motor,
        "motor",
        center=-0.5,
        Imax=1,
        sigma=1,
        labels={},
    )
    reg.register(cptA)
    reg.register(cptB)
    reg.register(cptC)
    # Pass the device names into the findall method
    result = reg.findall(["sample motor A", "sample motor B"])
    assert cptA in result
    assert cptB in result
    assert cptC not in result


def test_user_readback():
    """Edge case where EpicsMotor.user_readback is named the same as the motor itself."""
    registry = InstrumentRegistry()
    device = EpicsMotor("", name="epics_motor")
    registry.register(device)
    # See if requesting the device.user_readback returns the proper signal
    registry.find("epics_motor_user_readback")
