"""
Pytest configuration and fixtures for unit tests.
"""

import pytest


@pytest.fixture
def sample_fixture():
    """Sample fixture for unit tests."""
    return {"test": "data"}
