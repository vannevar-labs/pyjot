import pytest


@pytest.fixture(params=[{}, {"bink": 42}, {"bink": 42, "nork": 96}])
def dtags(request):
    return request.param


@pytest.fixture(params=[{}, {"floozy": 72}, {"bink": 64, "floozy": 72}])
def kwtags(request):
    return request.param


@pytest.fixture
def assert_tags_are_correct(dtags, kwtags):
    def fn(jot):
        tag_names = jot.tags.keys()

        # assert all keyword tags are present and correct
        for k, v in kwtags.items():
            assert k in tag_names
            assert jot.tags[k] == v

        # keyword tags override dictionary tags, so don't check those
        for k, v in dtags.items():
            if k in kwtags:
                continue
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
def child_tags(jot, dtags, kwtags):
    return {**jot.tags, **dtags, **kwtags}
