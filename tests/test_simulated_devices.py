from haven.instrument.load_instrument import load_simulated_devices

def test_load_simulated_devices(sim_registry):
    load_simulated_devices()
    # Check motors
    motor = sim_registry.find(name="sim_motor")
    # Check detectors
    detector = sim_registry.find(name="sim_detector")
