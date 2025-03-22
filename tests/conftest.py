import pytest


@pytest.fixture(params=[{}, {"floozy": 72}, {"bink": 64, "floozy": 72}])
def tags(request):
    return request.param


@pytest.fixture
def assert_tags_are_correct(tags):
    def fn(jot):
        tag_names = jot.tags.keys()

        # assert all keyword tags are present and correct
        for k, v in tags.items():
            assert k in tag_names
            assert jot.tags[k] == v

    return fn


@pytest.fixture
def assert_child_tags_are_correct(assert_tags_are_correct):
    def fn(parent, child):
        child_tag_names = child.tags.keys()
        for k, v in parent.tags.items():
            assert k in child_tag_names
            assert child.tags[k] == v
        assert_tags_are_correct(child)

    return fn


@pytest.fixture
def child_tags(jot, tags):
    return {**jot.tags, **tags}
