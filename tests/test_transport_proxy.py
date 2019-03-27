"""
Yandex Transport Proxy unit tests.

NOTE: These are Unit Tests, they should test function behaviour based on input data only, and should NOT
      rely on current state of Yandex API. These tests are executed once during "build" stage.
      Do not use Live Data from Yandex MassTransit here, only saved one. Live Data is tested in
      Integration Tests/Continuous Monitoring tests.
"""

import pytest

# ---------------------------------------------      warm-up        -------------------------------------------------- #

def test_initial():
    """
    Most basic test to ensure pytest DEFINITELY works
    """
    assert True == False
