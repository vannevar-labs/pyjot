#
# DO NOT RENAME THIS FILE
#
# This file must be imported last during test discovery. It iterates over all the subclasses of
# Target and runs test for each one. If it is not the last file imported, it will not find all
# the subclasses.
#

import pytest

from jot import log
from jot.base import Target

HEX_ALPHABET = "0123456789abcdef"


def target_subclasses():
    return list(all_subclasses(Target))


def all_subclasses(cls):
    yield cls
    for subclass in cls.__subclasses__():
        yield from all_subclasses(subclass)


@pytest.fixture
def cls(request):
    return request.param


def assert_is_hex(value):
    assert isinstance(value, str)
    for c in value:
        assert c in HEX_ALPHABET


@pytest.mark.parametrize("cls", target_subclasses(), indirect=True)
def test_accepts_log_level_equal(cls):
    accepted = False
    target = cls.default(level=log.INFO)
    if target.accepts_log_level(log.INFO):
        accepted = True
    assert accepted


@pytest.mark.parametrize("cls", target_subclasses(), indirect=True)
def test_accepts_log_level_lt(cls):
    accepted = False
    target = cls.default(log.INFO)
    if target.accepts_log_level(log.WARNING):
        accepted = True
    assert accepted


@pytest.mark.parametrize("cls", target_subclasses(), indirect=True)
def test_accepts_log_level_gt(cls):
    accepted = False
    target = cls.default(log.WARNING)
    if target.accepts_log_level(log.INFO):
        accepted = True
    assert not accepted
