from jot import log
from jot.base import Target


def test_default_constructor():
    target = Target()
    assert target.level == log.DEFAULT


def test_explicit_constructor():
    target = Target(log.INFO)
    assert target.level == log.INFO
