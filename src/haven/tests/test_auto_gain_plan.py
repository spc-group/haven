from queue import Queue

import numpy as np
import pytest
from bluesky_adaptive.recommendations import NoRecommendation

from haven import auto_gain, GainRecommender


def test_plan_recommendations(sim_ion_chamber):
    sim_ion_chamber.preamp.sensitivity_level.set(9).wait()
    # Make a fake queue that accepts the second step
    queue = Queue()
    queue.put({sim_ion_chamber.preamp.sensitivity_level.name: 10})
    queue.put(None)
    # Prepare the plan and make sure it generates messages
    plan = auto_gain(dets=[sim_ion_chamber], queue=queue)
    msgs = list(plan)
    # Make sure the plan sets the gain values properly
    set_msgs = [msg for msg in msgs if msg.command == "set"]
    assert len(set_msgs) == 2
    assert set_msgs[0].args[0] == 9.0  # Starting point
    assert set_msgs[1].args[0] == 10.0  # First adaptive point
    # Make sure the plan triggers the ion chamber
    trigger_msgs = [msg for msg in msgs if msg.command == "trigger"]
    assert len(trigger_msgs) == 2


@pytest.fixture()
def recommender():
    recc = GainRecommender()
    return recc


def test_recommender_all_low(recommender):
    """Does the engine get the right direction when all pre-amp gains are
    too low?

    """
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    # Corresponding volts
    volts = np.asarray([[0.1, 0.25]])
    assert volts.shape == (1, 2)
    # Check recommendations are lower by 3
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (7, 10))


def test_recommender_some_low(recommender):
    """Does the engine get the direction right when some pre-amp gains are
    too low and some are just right?

    """
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    # Corresponding volts
    volts = np.asarray([[0.1, 2.5]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (7, 12))


def test_recommender_all_high(recommender):
    """Does the engine get the direction correct when all pre-amp gains
    are too high?

    """
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    recommender.last_point = np.asarray([10, 13])
    # Corresponding volts
    volts = np.asarray([[4.6, 5.2]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (13, 16))


def test_recommender_some_high(recommender):
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    # Corresponding volts
    volts = np.asarray([[5.7, 2.5]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (13, 12))


def test_recommender_high_and_low(recommender):
    # Gain sensitivity levels
    gains = np.asarray([[10, 13]])
    assert gains.shape == (1, 2)
    # Corresponding volts
    volts = np.asarray([[5.7, 0.23]])
    assert volts.shape == (1, 2)
    # Check recommendations
    recommender.tell_many(gains, volts)
    np.testing.assert_equal(recommender.ask(1), (13, 10))


def test_recommender_fill_missing_gains(recommender):
    """If we have both high and low gains already done, will the
    recommender fill in the missing pieces."""
    gains = [[9], [12], [10],]
    volts = [[0.3], [5.2], [1.5],]
    recommender.tell_many(gains, volts)
    # Does it recommend the missing gain value?
    df = recommender.dfs[0]
    assert recommender.next_gain(df) == 10


def test_recommender_no_high(recommender):
    """If the gain happens to be in range first try, we need to get
    more data to be sure we have the best point.
    
    """
    gains = [[8], [9], [10]]
    volts = [[2.7], [1.25], [0.3]]
    recommender.tell_many(gains, volts)
    df = recommender.dfs[0]
    assert recommender.next_gain(df) == 7


def test_recommender_no_low(recommender):
    """If the gain happens to be in range first try, we need to get
    more data to be sure we have the best point.
    
    """
    gains = [[8], [9], [10]]
    volts = [[5.4], [2.75], [1.25]]
    recommender.tell_many(gains, volts)
    df = recommender.dfs[0]
    assert recommender.next_gain(df) == 11


def test_recommender_no_solution(recommender):
    """If the gain profile goes from too low to too high in one step, what should we report?"""
    gains = [[9], [10]]
    volts = [[0.3], [5.2]]
    recommender.tell_many(gains, volts)
    # Does it recommend the missing gain value?
    df = recommender.dfs[0]
    assert recommender.next_gain(df) == 9

def test_recommender_correct_solution(recommender):
    """If the gain profile goes from too low to too high in one step, what should we report?"""
    gains = [[8], [9], [10], [11]]
    volts = [[5.2], [2.7], [1.25], [0.4]]
    recommender.tell_many(gains, volts)
    # Does it recommend the missing gain value?
    df = recommender.dfs[0]
    assert recommender.next_gain(df) == 9


def test_recommender_no_change(recommender):
    """If we've already found the best solution, we should stop the scan."""
    # Set a history of gain measurements
    gains = np.asarray([
        [10, 13],
        [11, 11],
        [12, 14],
        [13, 12],
    ])
    volts = np.asarray([
        [7.10, 2.23],
        [4.30, 5.30],
        [2.10, 0.10],
        [0.20, 4.33],
    ])
    recommender.tell_many(gains, volts)
    # Make sure the engine recommends the best solution
    assert recommender.ask(1) == [12, 13]
    # Pass in results for this new measurement
    recommender.tell_many([[12, 13]], [[2.13, 2.19]])
    # Check recommendations
    with pytest.raises(NoRecommendation):
        recommender.ask(1)
