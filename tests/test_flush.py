import pytest

from jot.flush import add_handler, flush, remove_all_handlers, remove_handler


@pytest.fixture(autouse=True)
def handler():
    yield
    remove_all_handlers()


# plugins can add flush handlers, which will be called via flush()
def test_handler(mocker):
    mock_fn = mocker.Mock()
    add_handler(mock_fn)
    flush()
    assert mock_fn.called


# handlers can be removed
def test_remove():
    def fail():
        assert False

    add_handler(fail)
    remove_handler(fail)

    flush()


# handlers are called in reverse order
def test_handler_order():
    h1_has_been_called = False
    h2_has_been_called = False

    def h1():
        nonlocal h1_has_been_called, h2_has_been_called
        h1_has_been_called = True
        assert h2_has_been_called

    def h2():
        nonlocal h2_has_been_called, h2_has_been_called
        h2_has_been_called = True
        assert not h1_has_been_called

    add_handler(h1)
    add_handler(h2)

    flush()

    assert h2_has_been_called
    assert h1_has_been_called
