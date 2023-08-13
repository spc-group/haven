from haven.plans.fly import fly_scan


def test_set_fly_params(sim_aerotech_flyer):
    """Does the plan set the parameters of the flyer motor."""
    flyer = sim_aerotech_flyer
    # step size == 10
    plan = fly_scan(detectors=[], flyer=flyer, start=-20, stop=30, num=6, dwell_time=0.15)
    messages = list(plan)
    open_msg = messages[0]
    param_msgs = messages[1:5]
    fly_msgs = messages[5:-1]
    close_msg = messages[:-1]
    assert param_msgs[0].command == "set"
    assert param_msgs[1].command == "set"
    assert param_msgs[2].command == "set"
    assert param_msgs[3].command == "set"
    # Make sure the step size is calculated properly
    new_step_size = param_msgs[2].args[0]
    assert new_step_size == 10
