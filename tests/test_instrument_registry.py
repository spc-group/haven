from unittest import TestCase

from ophyd import sim, Device

from haven import exceptions
from haven.instrument import InstrumentRegistry


class InstrumentRegistryTests(TestCase):
    def test_register_component(self):
        # Prepare registry
        reg = InstrumentRegistry()
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
        with self.assertRaises(exceptions.ComponentNotFound):
            reg.find(label="ion_chamber")
        # Now register the component
        cpt = reg.register(cpt)
        # Confirm that it's findable by label
        results = reg.find(label="ion_chamber")
        self.assertIn(cpt, results)

    def test_find_missing_components(self):
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
        with self.assertRaises(exceptions.ComponentNotFound):
            reg.find(label="spam")

    def test_exceptions(self):
        reg = InstrumentRegistry()
        reg.register(Device("", name="It"))
        # Test if a list is given as a label key
        with self.assertRaises(exceptions.InvalidComponentLabel):
            reg.find(label=[Device("", name="I0")])
        # Test if a non-existent labels throws an exception
        with self.assertRaises(exceptions.ComponentNotFound):
            reg.find(label="spam")

    def test_as_class_decorator(self):
        reg = InstrumentRegistry()
        # Create a dummy decorated class
        IonChamber = type("IonChamber", (Device,), {})
        IonChamber = reg.register(IonChamber)
        # Instantiate the class
        ion_chamber = IonChamber("PV_PREFIX", name="I0", labels={"ion_chamber"})
        # Check that it gets retrieved
        result = reg.find(label="ion_chamber")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].prefix, "PV_PREFIX")
        self.assertEqual(result[0].name, "I0")
