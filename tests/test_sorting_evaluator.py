import numpy as np
from neuroflow.benchmark.sorting_evaluator import _matches


def test_matching_does_not_lose_second_available_candidate():
    # Nearest-neighbour deduplication incorrectly returns one for this case.
    assert _matches(np.array([0.1, 0.2]), np.array([0.15, 0.3]), 0.11) == 2


def test_candidate_spike_cannot_be_reused():
    assert _matches(np.array([0.1, 0.2]), np.array([0.15]), 0.11) == 1
