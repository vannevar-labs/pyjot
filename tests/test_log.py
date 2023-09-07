import importlib
import os

import pytest

import jot.log


@pytest.fixture
def log_level_info():
    os.environ["LOG_LEVEL"] = "INFO"
    yield
    del os.environ["LOG_LEVEL"]


@pytest.fixture
def log_level_all():
    os.environ["LOG_LEVEL"] = "ALL"
    yield
    del os.environ["LOG_LEVEL"]


def test_default_default():
    assert jot.log.DEFAULT == jot.log.WARNING


def test_default_info(log_level_info):
    importlib.reload(jot.log)
    assert jot.log.DEFAULT == jot.log.INFO


def test_default_all(log_level_all):
    importlib.reload(jot.log)
    assert jot.log.DEFAULT == jot.log.ALL
    assert jot.log.DEFAULT == jot.log.ALL
