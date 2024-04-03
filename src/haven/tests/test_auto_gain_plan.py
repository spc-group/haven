from queue import Queue

import numpy as np
import pytest
from bluesky_adaptive.recommendations import NoRecommendation

from haven import GainRecommender, auto_gain


def test_plan_recommendations(sim_ion_chamber):
    sim_ion_chamber.preamp.gain_level.set(18).wait()
    # Make a fake queue that accepts the second step
    queue = Queue()
    queue.put({sim_ion_chamber.preamp.gain_level.name: 17})
    queue.put(None)
    # Prepare the plan and make sure it generates messages
    plan = auto_gain(dets=[sim_ion_chamber], queue=queue)
    msgs = list(plan)
    # Make sure the plan sets the gain values properly
    set_msgs = [msg for msg in msgs if msg.command == "set"]
    assert len(set_msgs) == 2
    assert set_msgs[0].args[0] == 18  # Starting point
    assert set_msgs[1].args[0] == 17  # First adaptive point
    # Make sure the plan triggers the ion chamber
    trigger_msgs = [msg for msg in msgs if msg.command == "trigger"]
    assert len(trigger_msgs) == 2


@pytest.fixture()
def recommender():
    recc = GainRecommender()
    return recc


def test_recommender_all_low(recommender):
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    # Corresponding volts
    volts = np.asarray([[0.1, 0.25]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (9, 12))


def test_recommender_some_low(recommender):
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    recommender.last_point = np.asarray([10, 13])
    # Corresponding volts
    volts = np.asarray([[0.1, 2.5]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (9, 13))


def test_recommender_all_high(recommender):
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    recommender.last_point = np.asarray([10, 13])
    # Corresponding volts
    volts = np.asarray([[4.6, 5.2]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (11, 14))


def test_recommender_some_high(recommender):
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    recommender.last_point = np.asarray([10, 13])
    # Corresponding volts
    volts = np.asarray([[5.7, 2.5]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (11, 13))


def test_recommender_high_and_low(recommender):
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    recommender.last_point = np.asarray([10, 13])
    # Corresponding volts
    volts = np.asarray([[5.7, 0.23]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (11, 12))


def test_recommender_no_change(recommender):
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    # Corresponding volts
    volts = np.asarray([[4.1, 2.23]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    with pytest.raises(NoRecommendation):
        recommender.ask(1)


def test_recommender_hysteresis(recommender):
    """Test that we can avoid getting caught at the bottom of the voltage
    range."""
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    # Corresponding volts
    volts = np.asarray([[0.1, 2.3]])
    recommender.last_point = np.asarray([10, 14])
    assert volts.shape == (1, 2)
    # Check recommendations, second gain should still go up
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (9, 12))
