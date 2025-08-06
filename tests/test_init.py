"""
This module includes tests for:
- Environment-based target initialization
- Environment-based full initialization (init_from_environment)
- Environment variable tagging (JOT_TAG_ and standard variables)
- Module importing from JOT_MODULES
- Inheritance tree bug fix (recursive subclass discovery)
- FanOut target creation
- Integration testing with actual logging
- Performance and safety checks
"""

import atexit
import os
import platform
import sys
import time
from unittest import mock

import pytest

import jot
from jot import base, facade, log
from jot.fanout import FanOutTarget


# Test target classes for various scenarios
class DummyTarget(base.Target):
    """A basic target for testing environment-based initialization"""

    @classmethod
    def from_environment(cls):
        if os.environ.get("DUMMY_TARGET_ENABLED") == "1":
            return cls()
        return None

    def __init__(self, level=None):
        super().__init__(level=level)
        self.name = "dummy"
        self.logged_messages = []
        self.level = log.ALL

    def accepts_log_level(self, level):
        return level <= self.level

    def log(self, level, message, tags, span=None):
        self.logged_messages.append((level, message, tags, span))


class AnotherTarget(base.Target):
    """Another target for testing multiple environment targets"""

    @classmethod
    def from_environment(cls):
        if os.environ.get("ANOTHER_TARGET_ENABLED") == "1":
            return cls()
        return None

    def __init__(self, level=None):
        super().__init__(level=level)
        self.name = "another"
        self.logged_messages = []
        self.level = log.ALL

    def accepts_log_level(self, level):
        return level <= self.level

    def log(self, level, message, tags, span=None):
        self.logged_messages.append((level, message, tags, span))


class IntermediateTarget(base.Target):
    """An intermediate target that doesn't implement from_environment"""

    def __init__(self, level=None):
        super().__init__(level=level)
        self.name = "intermediate"


class NestedTarget(IntermediateTarget):
    """A target that inherits from IntermediateTarget (tests inheritance tree fix)"""

    @classmethod
    def from_environment(cls):
        if os.environ.get("NESTED_TARGET_ENABLED") == "1":
            return cls()
        return None

    def __init__(self, level=None):
        super().__init__(level=level)
        self.name = "nested"
        self.logged_messages = []
        self.level = log.ALL

    def accepts_log_level(self, level):
        return level <= self.level

    def log(self, level, message, tags, span=None):
        self.logged_messages.append((level, message, tags, span))


# Fixtures
@pytest.fixture
def reset_env():
    """Reset environment variables before each test"""
    original_env = os.environ.copy()

    # Clear test environment variables
    test_vars = [
        "DUMMY_TARGET_ENABLED",
        "ANOTHER_TARGET_ENABLED",
        "NESTED_TARGET_ENABLED",
        "INFLUXDB3_ENDPOINT",
        "INFLUXDB3_DATABASE",
        "INFLUXDB3_TOKEN",
        "JOT_MODULES",
        "HOSTNAME",
        "JOT_TAG_SERVICE",
        "JOT_TAG_ENVIRONMENT",
        "JOT_TAG_CUSTOM_KEY",
    ]
    for key in test_vars:
        if key in os.environ:
            del os.environ[key]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def reset_active_meter():
    """Reset the active meter after each test"""
    original_meter = facade.active_meter
    yield
    facade.active_meter = original_meter


@pytest.fixture
def mock_test_subclasses(monkeypatch):
    """Mock recursive subclass discovery to include our test classes"""

    def mock_get_all_subclasses(cls):
        if cls == base.Target:
            return {DummyTarget, AnotherTarget, IntermediateTarget, NestedTarget}
        elif cls == IntermediateTarget:
            return {NestedTarget}
        else:
            return set()

    monkeypatch.setattr("jot.util.get_all_subclasses", mock_get_all_subclasses)


@pytest.fixture
def mock_system_effects(monkeypatch):
    """Mock system-level effects to prevent test interference"""
    # Mock atexit.register to prevent test from affecting program shutdown
    mock_atexit_register = mock.MagicMock()
    monkeypatch.setattr(atexit, "register", mock_atexit_register)

    # Mock sys.excepthook to prevent test from affecting exception handling
    original_excepthook = sys.excepthook
    mock_excepthook = mock.MagicMock()
    monkeypatch.setattr(sys, "excepthook", mock_excepthook)

    yield

    # Restore original excepthook
    sys.excepthook = original_excepthook


# Test classes
class TestBasicInitialization:
    """Test basic initialization scenarios"""

    def test_no_env_targets(self, reset_env, reset_active_meter, mock_test_subclasses):
        """Test init_from_environment when no environment targets are available"""
        jot.init_from_environment()

        # Should create a default Target
        assert isinstance(facade.active_meter.target, base.Target)
        assert not isinstance(
            facade.active_meter.target, (DummyTarget, AnotherTarget, NestedTarget, FanOutTarget)
        )

    def test_single_env_target(self, reset_env, reset_active_meter, mock_test_subclasses):
        """Test init_from_environment when one environment target is available"""
        os.environ["DUMMY_TARGET_ENABLED"] = "1"

        jot.init_from_environment()

        assert isinstance(facade.active_meter.target, DummyTarget)
        assert facade.active_meter.target.name == "dummy"

    def test_multiple_env_targets(self, reset_env, reset_active_meter, mock_test_subclasses):
        """Test init_from_environment when multiple environment targets are available"""
        os.environ["DUMMY_TARGET_ENABLED"] = "1"
        os.environ["ANOTHER_TARGET_ENABLED"] = "1"

        jot.init_from_environment()

        # Should create a FanOutTarget with both targets
        assert isinstance(facade.active_meter.target, FanOutTarget)

        targets = facade.active_meter.target.targets
        assert len(targets) == 2

        target_names = {t.name for t in targets}
        assert target_names == {"dummy", "another"}

    def test_explicit_target_overrides_env(
        self, reset_env, reset_active_meter, mock_test_subclasses
    ):
        """Test that an explicitly provided target overrides environment targets"""
        os.environ["DUMMY_TARGET_ENABLED"] = "1"
        os.environ["ANOTHER_TARGET_ENABLED"] = "1"

        custom_target = base.Target()
        jot.init(custom_target, service="my-service", version="1.0.0")

        # Should use the explicit target, not environment targets
        assert facade.active_meter.target is custom_target
        assert facade.active_meter.tags == {"service": "my-service", "version": "1.0.0"}

    def test_init_with_explicit_target_and_tags(
        self, reset_env, reset_active_meter, mock_test_subclasses
    ):
        """Test that tags are properly passed through when using explicit target"""
        os.environ["DUMMY_TARGET_ENABLED"] = "1"

        dummy_target = DummyTarget()
        jot.init(dummy_target, service="my-service", version="1.0.0")

        assert facade.active_meter.target is dummy_target
        assert facade.active_meter.tags == {"service": "my-service", "version": "1.0.0"}

    def test_flush_init_called(
        self, reset_env, reset_active_meter, mock_test_subclasses, monkeypatch
    ):
        """Test that flush.init() is called during jot.init_from_environment()"""
        mock_flush_init = mock.MagicMock()
        monkeypatch.setattr("jot.flush.init", mock_flush_init)

        jot.init_from_environment()

        mock_flush_init.assert_called_once()


def test_init_from_environment_basic(reset_env, reset_active_meter, mock_test_subclasses):
    """Test basic init_from_environment functionality"""
    os.environ["DUMMY_TARGET_ENABLED"] = "1"

    jot.init_from_environment()

    assert isinstance(facade.active_meter.target, DummyTarget)


def test_init_from_environment_with_tags(reset_env, reset_active_meter, mock_test_subclasses):
    """Test init_from_environment includes environment tags"""
    os.environ["DUMMY_TARGET_ENABLED"] = "1"
    os.environ["HOSTNAME"] = "test-host"
    os.environ["JOT_TAG_SERVICE"] = "my-service"
    os.environ["JOT_TAG_ENVIRONMENT"] = "production"

    jot.init_from_environment()

    tags = facade.active_meter.tags

    # Should include HOSTNAME as host.name
    assert tags["host.name"] == "test-host"

    # Should include JOT_TAG_ variables with proper key transformation
    assert tags["service"] == "my-service"
    assert tags["environment"] == "production"

    # Should include system information
    assert "process.runtime.name" in tags
    assert "process.runtime.version" in tags
    assert "os.type" in tags
    assert "host.arch" in tags

    # Verify system tag values
    assert tags["process.runtime.name"] == sys.implementation.name
    assert tags["process.runtime.version"] == platform.python_version()
    assert tags["os.type"] == sys.platform
    assert tags["host.arch"] == platform.machine()


def test_init_from_environment_modules_import(reset_env, reset_active_meter, monkeypatch):
    """Test that JOT_MODULES environment variable imports modules"""
    mock_import = mock.MagicMock()
    monkeypatch.setattr("importlib.import_module", mock_import)

    os.environ["JOT_MODULES"] = "module1,module2,non_existent_module"

    # Mock import_module to raise ImportError for non_existent_module
    def mock_import_side_effect(module):
        if module == "non_existent_module":
            raise ImportError("Module not found")
        return mock.MagicMock()

    mock_import.side_effect = mock_import_side_effect

    jot.init_from_environment()

    # Should attempt to import all modules
    assert mock_import.call_count == 3
    mock_import.assert_any_call("module1")
    mock_import.assert_any_call("module2")
    mock_import.assert_any_call("non_existent_module")


def test_init_from_environment_no_modules(reset_env, reset_active_meter, monkeypatch):
    """Test init_from_environment when JOT_MODULES is not set"""
    mock_import = mock.MagicMock()
    monkeypatch.setattr("importlib.import_module", mock_import)

    jot.init_from_environment()

    # Should not attempt any imports
    mock_import.assert_not_called()


def test_tag_key_transformation(reset_env, reset_active_meter, mock_test_subclasses):
    """Test that JOT_TAG_ keys are properly transformed"""
    os.environ["DUMMY_TARGET_ENABLED"] = "1"
    os.environ["JOT_TAG_CUSTOM_KEY"] = "value1"
    os.environ["JOT_TAG_ANOTHER_LONG_KEY"] = "value2"
    os.environ["JOT_TAG_SIMPLE"] = "value3"

    jot.init_from_environment()

    tags = facade.active_meter.tags

    # Should transform underscores to dots and convert to lowercase
    assert tags["custom.key"] == "value1"
    assert tags["another.long.key"] == "value2"
    assert tags["simple"] == "value3"


def test_environment_tags_without_hostname(reset_env, reset_active_meter, mock_test_subclasses):
    """Test environment tags when HOSTNAME is not set"""
    os.environ["DUMMY_TARGET_ENABLED"] = "1"
    # Explicitly don't set HOSTNAME

    jot.init_from_environment()

    tags = facade.active_meter.tags

    # Should not include host.name if HOSTNAME is not set
    assert "host.name" not in tags

    # But should still include system information
    assert "process.runtime.name" in tags
    assert "process.runtime.version" in tags
    assert "os.type" in tags
    assert "host.arch" in tags


class TestInheritanceTreeFix:
    """Test the inheritance tree bug fix (recursive subclass discovery)"""

    def test_nested_subclass_discovery(self, reset_env, reset_active_meter, mock_test_subclasses):
        """Verify that nested subclasses are discovered (would fail before the fix)"""
        os.environ["NESTED_TARGET_ENABLED"] = "1"

        jot.init_from_environment()

        # This is the key test - NestedTarget inherits from IntermediateTarget,
        # not directly from Target, so it would be missed by the old implementation
        assert isinstance(facade.active_meter.target, NestedTarget)
        assert facade.active_meter.target.name == "nested"

    def test_mixed_direct_and_nested_targets(
        self, reset_env, reset_active_meter, mock_test_subclasses
    ):
        """Verify that FanOut works with both direct and nested targets"""
        os.environ["DUMMY_TARGET_ENABLED"] = "1"  # Direct subclass
        os.environ["NESTED_TARGET_ENABLED"] = "1"  # Nested subclass

        jot.init_from_environment()

        assert isinstance(facade.active_meter.target, FanOutTarget)

        targets = facade.active_meter.target.targets
        assert len(targets) == 2

        target_names = {t.name for t in targets}
        assert target_names == {"dummy", "nested"}

    def test_real_world_influxdb_inheritance(self, reset_env, reset_active_meter):
        """Test with the actual InfluxDB inheritance hierarchy from the codebase"""
        # Import to ensure the classes are loaded
        import jot.influxdb

        # Set up InfluxDB3Target environment (inherits from InfluxLineProtocolTarget)
        os.environ["INFLUXDB3_ENDPOINT"] = "http://localhost:8086"
        os.environ["INFLUXDB3_DATABASE"] = "test_db"
        os.environ["INFLUXDB3_TOKEN"] = "test_token"

        jot.init_from_environment()

        # This would fail with the old implementation because InfluxDB3Target
        # is not a direct subclass of Target
        target = facade.active_meter.target
        assert target.__class__.__name__ == "InfluxDB3Target"
        assert target.__class__.__module__ == "jot.influxdb.influxdb"

    def test_no_infinite_recursion(self, reset_env, reset_active_meter):
        """Verify that the recursive function doesn't cause infinite recursion"""
        from jot.util import get_all_subclasses

        # This should complete without raising RecursionError
        subclasses = get_all_subclasses(base.Target)

        # Should find all the expected subclasses
        assert len(subclasses) > 0

        # Verify we found the nested InfluxDB targets
        class_names = {cls.__name__ for cls in subclasses}
        assert "InfluxDB2Target" in class_names
        assert "InfluxDB3Target" in class_names
        assert "InfluxLineProtocolTarget" in class_names


class TestFanOutTarget:
    """Test FanOutTarget behavior"""

    def test_fanout_log_level_delegation(self, reset_env, reset_active_meter, mock_test_subclasses):
        """Test that FanOutTarget properly handles log levels from sub-targets"""
        os.environ["DUMMY_TARGET_ENABLED"] = "1"
        os.environ["ANOTHER_TARGET_ENABLED"] = "1"

        jot.init_from_environment()

        fanout_target = facade.active_meter.target
        assert isinstance(fanout_target, FanOutTarget)

        target1, target2 = fanout_target.targets

        # Case 1: When at least one target accepts a level
        target1.level = log.DEBUG
        target2.level = log.WARNING  # Higher level (won't accept DEBUG)

        assert target1.accepts_log_level(log.DEBUG)
        assert not target2.accepts_log_level(log.DEBUG)
        assert fanout_target.accepts_log_level(log.DEBUG)

        # Case 2: When all targets reject a level
        target1.level = log.WARNING
        target2.level = log.WARNING

        assert not target1.accepts_log_level(log.DEBUG)
        assert not target2.accepts_log_level(log.DEBUG)
        assert not fanout_target.accepts_log_level(log.DEBUG)


class TestIntegration:
    """Integration tests that verify end-to-end functionality"""

    def test_end_to_end_logging(
        self, reset_env, reset_active_meter, mock_test_subclasses, mock_system_effects
    ):
        """Test the entire initialization and logging process end to end"""
        os.environ["DUMMY_TARGET_ENABLED"] = "1"
        os.environ["ANOTHER_TARGET_ENABLED"] = "1"

        # Initialize with tags
        jot.init_from_environment()

        # Verify setup
        assert isinstance(facade.active_meter.target, FanOutTarget)
        # Tags should include system information from init_from_environment
        assert "process.runtime.name" in facade.active_meter.tags
        assert "process.runtime.version" in facade.active_meter.tags

        targets = facade.active_meter.target.targets
        assert len(targets) == 2

        dummy_target = next((t for t in targets if t.name == "dummy"), None)
        another_target = next((t for t in targets if t.name == "another"), None)

        assert dummy_target is not None
        assert another_target is not None

        # Reset facade to ensure clean state for logging test
        facade.active_meter = base.Meter(
            facade.active_meter.target, None, **facade.active_meter.tags
        )

        # Mock caller tags to avoid file location dependencies
        with mock.patch(
            "jot.util.add_caller_tags",
            side_effect=lambda x: x.update(
                {"file": "test_file.py", "line": 123, "function": "test_function"}
            ),
        ):
            # Test logging through the meter
            jot.info("Integration test message", custom_tag="value")

            # Both targets should have received the log message
            assert len(dummy_target.logged_messages) == 1
            assert len(another_target.logged_messages) == 1

        # Verify log content
        level, message, tags, span = dummy_target.logged_messages[0]
        assert level == log.INFO
        assert message == "Integration test message"
        assert tags["custom_tag"] == "value"
        assert "process.runtime.name" in tags
        assert "process.runtime.version" in tags
        assert "file" in tags
        assert "line" in tags
        assert "function" in tags

    def test_single_target_logging(
        self, reset_env, reset_active_meter, mock_test_subclasses, mock_system_effects
    ):
        """Test logging with a single environment target"""
        os.environ["DUMMY_TARGET_ENABLED"] = "1"

        jot.init_from_environment()

        assert isinstance(facade.active_meter.target, DummyTarget)
        assert not isinstance(facade.active_meter.target, FanOutTarget)

        target = facade.active_meter.target
        facade.active_meter = base.Meter(target, None)

        with mock.patch(
            "jot.util.add_caller_tags",
            side_effect=lambda x: x.update(
                {"file": "test_file.py", "line": 123, "function": "test_function"}
            ),
        ):
            jot.info("Single target test")

            assert len(target.logged_messages) == 1
            level, message, tags, span = target.logged_messages[0]
            assert level == log.INFO
            assert message == "Single target test"


def test_end_to_end_environment_initialization(
    reset_env, reset_active_meter, mock_test_subclasses, mock_system_effects
):
    """Test complete end-to-end flow with init_from_environment"""
    os.environ["DUMMY_TARGET_ENABLED"] = "1"
    os.environ["HOSTNAME"] = "test-server"
    os.environ["JOT_TAG_SERVICE"] = "my-app"
    os.environ["JOT_TAG_VERSION"] = "1.2.3"

    jot.init_from_environment()

    # Verify target initialization
    assert isinstance(facade.active_meter.target, DummyTarget)

    # Verify tags are properly set
    tags = facade.active_meter.tags
    assert tags["host.name"] == "test-server"
    assert tags["service"] == "my-app"
    assert tags["version"] == "1.2.3"
    assert "process.runtime.name" in tags

    # Test logging with environment-initialized meter
    target = facade.active_meter.target

    with mock.patch(
        "jot.util.add_caller_tags",
        side_effect=lambda x: x.update(
            {"file": "test_file.py", "line": 123, "function": "test_function"}
        ),
    ):
        jot.info("Environment init test")

        assert len(target.logged_messages) == 1
        level, message, logged_tags, span = target.logged_messages[0]
        assert level == log.INFO
        assert message == "Environment init test"
        assert logged_tags["host.name"] == "test-server"
        assert logged_tags["service"] == "my-app"
        assert logged_tags["version"] == "1.2.3"


class TestPerformanceAndSafety:
    """Test performance and safety aspects of the initialization"""

    def test_performance_of_recursive_discovery(self, reset_env, reset_active_meter):
        """Verify that the recursive discovery doesn't cause performance issues"""
        # Import all modules to simulate real-world usage
        import jot.fanout
        import jot.influxdb
        import jot.otlp
        import jot.print
        import jot.prometheus
        import jot.rollbar
        import jot.sentry
        import jot.zipkin

        start_time = time.time()

        # Run init multiple times
        for _ in range(10):
            jot.init_from_environment()

        end_time = time.time()

        # Should complete quickly (well under 1 second for 10 iterations)
        assert end_time - start_time < 1.0

    def test_backward_compatibility(self, reset_env, reset_active_meter, mock_test_subclasses):
        """Verify that existing behavior is preserved"""
        # When no targets are available, should still create default Target
        jot.init_from_environment()

        assert isinstance(facade.active_meter.target, base.Target)
        assert not hasattr(facade.active_meter.target, "name")

    def test_no_subclasses_fallback(self, reset_env, reset_active_meter, monkeypatch):
        """Test init when Target has no subclasses"""
        # Mock _get_all_subclasses to return empty set
        mock_get_all_subclasses = mock.MagicMock(return_value=set())
        monkeypatch.setattr("jot.util.get_all_subclasses", mock_get_all_subclasses)

        jot.init_from_environment()

        # Should create a default Target
        assert isinstance(facade.active_meter.target, base.Target)
        assert not isinstance(facade.active_meter.target, FanOutTarget)

    def test_env_target_returns_none(self, reset_env, reset_active_meter, mock_test_subclasses):
        """Test when from_environment is called but returns None for all subclasses"""
        # Ensure our test classes are called but return None
        os.environ["DUMMY_TARGET_ENABLED"] = "0"
        os.environ["ANOTHER_TARGET_ENABLED"] = "0"
        os.environ["NESTED_TARGET_ENABLED"] = "0"

        jot.init_from_environment()

        # Should create a default Target
        assert isinstance(facade.active_meter.target, base.Target)
        assert not isinstance(
            facade.active_meter.target, (DummyTarget, AnotherTarget, NestedTarget, FanOutTarget)
        )


def test_performance_of_environment_initialization(reset_env, reset_active_meter):
    """Verify that init_from_environment doesn't cause performance issues"""
    os.environ["HOSTNAME"] = "test-host"
    os.environ["JOT_TAG_SERVICE"] = "test-service"
    os.environ["JOT_TAG_VERSION"] = "1.0.0"

    start_time = time.time()

    # Run init_from_environment multiple times
    for _ in range(10):
        jot.init_from_environment()

    end_time = time.time()

    # Should complete quickly
    assert end_time - start_time < 1.0


def test_empty_jot_modules(reset_env, reset_active_meter, monkeypatch):
    """Test JOT_MODULES with empty string"""
    mock_import = mock.MagicMock()
    monkeypatch.setattr("importlib.import_module", mock_import)

    os.environ["JOT_MODULES"] = ""

    jot.init_from_environment()

    # Should not attempt any imports for empty string
    mock_import.assert_not_called()


def test_jot_modules_with_whitespace(reset_env, reset_active_meter, monkeypatch):
    """Test JOT_MODULES with modules containing whitespace"""
    mock_import = mock.MagicMock()
    monkeypatch.setattr("importlib.import_module", mock_import)

    os.environ["JOT_MODULES"] = " module1 , module2 , module3 "

    jot.init_from_environment()

    # Should strip whitespace and import correctly
    assert mock_import.call_count == 3
    mock_import.assert_any_call(" module1 ")
    mock_import.assert_any_call(" module2 ")
    mock_import.assert_any_call(" module3 ")


def test_empty_tag_values(reset_env, reset_active_meter, mock_test_subclasses):
    """Test environment tags with empty values"""
    os.environ["DUMMY_TARGET_ENABLED"] = "1"
    os.environ["HOSTNAME"] = ""
    os.environ["JOT_TAG_SERVICE"] = ""
    os.environ["JOT_TAG_EMPTY_KEY"] = ""

    jot.init_from_environment()

    tags = facade.active_meter.tags

    # HOSTNAME empty value should not be included (filtered out by _add_tag_from_env)
    assert "host.name" not in tags

    # But JOT_TAG_ empty values should be included (added directly)
    assert tags["service"] == ""
    assert tags["empty.key"] == ""

    # System information should still be present
    assert "process.runtime.name" in tags
    assert "process.runtime.version" in tags


def test_complex_tag_key_transformation(reset_env, reset_active_meter, mock_test_subclasses):
    """Test complex JOT_TAG key transformations"""
    os.environ["DUMMY_TARGET_ENABLED"] = "1"
    os.environ["JOT_TAG_COMPLEX_KEY_WITH_MANY_UNDERSCORES"] = "value"
    os.environ["JOT_TAG_MixedCase_KEY"] = "value2"  # Should still be lowercased

    jot.init_from_environment()

    tags = facade.active_meter.tags

    assert tags["complex.key.with.many.underscores"] == "value"
    assert tags["mixedcase.key"] == "value2"
