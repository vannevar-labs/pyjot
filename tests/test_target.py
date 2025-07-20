from jot import log
from jot.base import Target


def test_default_constructor():
    target = Target()
    assert target.level == log.DEFAULT


def test_explicit_constructor():
    target = Target(log.INFO)
    assert target.level == log.INFO


def test_accepts_log_level_equal():
    target = Target(level=log.INFO)
    assert target.accepts_log_level(log.INFO)


def test_accepts_log_level_lt():
    target = Target(log.INFO)
    assert target.accepts_log_level(log.WARNING)


def test_accepts_log_level_gt():
    target = Target(log.WARNING)
    assert not target.accepts_log_level(log.INFO)
