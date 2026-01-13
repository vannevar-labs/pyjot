import inspect

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


def is_test_function(name):
    if name in ["jot", "args", "select"]:
        return False
    if name.startswith("_"):
        return False
    return True


def decorated_functions():
    from . import decorated_fn as fn

    return [getattr(fn, name) for name in dir(fn) if is_test_function(name)]


def pytest_generate_tests(metafunc):
    if "func" in metafunc.fixturenames:
        fns = decorated_functions()

        # filter by function type
        if inspect.iscoroutinefunction(metafunc.function):
            fns = [
                fn
                for fn in fns
                if inspect.iscoroutinefunction(fn)
                or inspect.isasyncgenfunction(fn)
                or "async_generator" in getattr(fn, "_jot_selectors", set())
            ]
        else:
            fns = [
                fn
                for fn in fns
                if not inspect.iscoroutinefunction(fn)
                and not inspect.isasyncgenfunction(fn)
                and "async_generator" not in getattr(fn, "_jot_selectors", set())
            ]

        # filter by selectors marks, if any
        for markinfo in metafunc.definition.iter_markers():
            if markinfo.name == "select":
                test_selectors = set(markinfo.args)
                _fns = []
                for fn in fns:
                    fn_selectors = getattr(fn, "_jot_selectors", set())
                    if test_selectors.issubset(fn_selectors):
                        _fns.append(fn)
                fns = _fns
            if markinfo.name == "reject":
                test_selectors = set(markinfo.args)
                _fns = []
                for fn in fns:
                    fn_selectors = getattr(fn, "_jot_selectors", set())
                    if not test_selectors.intersection(fn_selectors):
                        _fns.append(fn)
                fns = _fns

        # Exclude generator functions from non-generator tests
        test_name = metafunc.function.__name__
        if "generator" not in test_name:
            _fns = []
            for fn in fns:
                fn_selectors = getattr(fn, "_jot_selectors", set())
                # Exclude functions marked as generators from non-generator tests
                if not ("sync_generator" in fn_selectors or "async_generator" in fn_selectors):
                    _fns.append(fn)
            fns = _fns

        # parametrize by args and kwargs, if the function requests both
        if "args" in metafunc.fixturenames and "kwargs" in metafunc.fixturenames:
            params = []
            for fn in fns:
                for args, kwargs in getattr(fn, "_jot_args", []):
                    params.append((fn, args, kwargs))
            metafunc.parametrize(["func", "args", "kwargs"], params)

        # parametrize by args only, if the function requests it
        elif "args" in metafunc.fixturenames:
            params = []
            for fn in fns:
                for args, _ in getattr(fn, "_jot_args", []):
                    params.append((fn, args))
            metafunc.parametrize(["func", "args"], params)

        # parametrize by kwargs only, if the function requests it
        elif "kwargs" in metafunc.fixturenames:
            params = []
            for fn in fns:
                for _, kwargs in getattr(fn, "_jot_args", []):
                    params.append((fn, kwargs))
            metafunc.parametrize(["func", "kwargs"], params)

        # parametrize by function only
        else:
            metafunc.parametrize("func", fns)
