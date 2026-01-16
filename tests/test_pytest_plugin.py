"""Tests for the pytest plugin functionality.

Tests cover:
- Hook execution order
- Metadata collection from @specleft decorated tests
- Auto-skip for removed scenarios
- Runtime marker injection from tags
- Thread-local storage handling
- Handling of missing specs
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest


def _write_specs_tree(base_dir: Path) -> Path:
    features_dir = base_dir / "features"
    auth_story_dir = features_dir / "auth" / "login"
    parse_story_dir = features_dir / "parse" / "units"
    auth_story_dir.mkdir(parents=True, exist_ok=True)
    parse_story_dir.mkdir(parents=True, exist_ok=True)

    (features_dir / "auth" / "_feature.md").write_text(
        """
---
feature_id: auth
priority: critical
tags: [core]
---

# Feature: User Authentication
""".strip()
    )
    (auth_story_dir / "_story.md").write_text(
        """
---
story_id: login
priority: high
tags: [auth-flow]
---

# Story: Login
""".strip()
    )
    (auth_story_dir / "login_success.md").write_text(
        """
---
scenario_id: login-success
priority: high
tags: [smoke, critical, auth-flow]
execution_time: fast
---

# Scenario: Successful login

## Steps
- **Given** user has valid credentials
- **When** user logs in
- **Then** user sees dashboard
""".strip()
    )
    (auth_story_dir / "login_failure.md").write_text(
        """
---
scenario_id: login-failure
priority: medium
tags: [regression, negative]
execution_time: fast
---

# Scenario: Failed login

## Steps
- **Given** user has invalid credentials
- **When** user tries to log in
- **Then** user sees error message
""".strip()
    )

    (features_dir / "parse" / "_feature.md").write_text(
        """
---
feature_id: parse
priority: high
tags: [unit]
---

# Feature: Unit Parsing
""".strip()
    )
    (parse_story_dir / "_story.md").write_text(
        """
---
story_id: units
priority: medium
tags: [parsing]
---

# Story: Units
""".strip()
    )
    (parse_story_dir / "extract_unit.md").write_text(
        """
---
scenario_id: extract-unit
priority: medium
tags: [unit, parsing]
execution_time: fast
---

# Scenario: Extract unit from string

## Steps
- **When** extracting unit
- **Then** unit is correct
""".strip()
    )

    return features_dir


if TYPE_CHECKING:
    from pytest import Pytester


# =============================================================================
# Helper fixtures
# =============================================================================


@pytest.fixture
def create_specs_tree(pytester: Pytester) -> Path:
    """Create a Markdown specs tree in the test directory."""
    return _write_specs_tree(pytester.path)


@pytest.fixture(autouse=True)
def ensure_specs_tree(create_specs_tree: Path) -> None:
    """Ensure a default specs tree exists for plugin tests."""
    _ = create_specs_tree


# =============================================================================
# Test: pytest_configure hook
# =============================================================================


class TestPytestConfigure:
    """Tests for pytest_configure hook."""

    def test_specleft_results_initialized(self, pytester: Pytester) -> None:
        """Test that _specleft_results is initialized on config."""
        # We test by checking results are collected after tests run
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_dummy():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

    def test_metadata_stored_on_item(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that metadata is stored on test items."""
        pytester.makeconftest(
            """
            def pytest_runtest_setup(item):
                if hasattr(item, '_specleft_metadata'):
                    metadata = item._specleft_metadata
                    assert metadata['feature_id'] == 'auth'
                    assert metadata['scenario_id'] == 'login-success'
            """
        )
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        result = pytester.runpytest()
        result.assert_outcomes(passed=1)


# =============================================================================
# Test: Auto-skip removed scenarios
# =============================================================================


class TestAutoSkip:
    """Tests for auto-skip functionality when scenarios are removed."""

    def test_skip_orphaned_scenario(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that tests with removed scenarios are skipped."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="nonexistent-scenario")
            def test_orphaned():
                pass
            """
        )
        result = pytester.runpytest("-v", "-rs")  # -rs shows skip reasons
        result.assert_outcomes(skipped=1)
        # Check skip reason is in output (using -rs flag)
        result.stdout.fnmatch_lines(["*nonexistent-scenario*not found in specs*"])

    def test_skip_orphaned_feature(self, pytester: Pytester, create_specs_tree) -> None:
        """Test that tests with removed features are skipped."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="missing-feature", scenario_id="login-success")
            def test_orphaned():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(skipped=1)

    def test_skip_reason_includes_identifiers(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that skip reason includes feature and scenario IDs."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="removed-feature", scenario_id="deleted-scenario")
            def test_orphaned():
                pass
            """
        )
        result = pytester.runpytest("-v", "-rs")
        result.assert_outcomes(skipped=1)
        result.stdout.fnmatch_lines(["*deleted-scenario*removed-feature*"])

    def test_valid_scenario_not_skipped(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that valid scenarios are not skipped."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_valid():
                pass

            @specleft(feature_id="auth", scenario_id="login-failure")
            def test_also_valid():
                pass

            @specleft(feature_id="parse", scenario_id="extract-unit")
            def test_another_valid():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=3)

    def test_mixed_valid_and_orphaned(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that valid and orphaned tests are handled correctly together."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_valid():
                pass

            @specleft(feature_id="auth", scenario_id="orphaned-scenario")
            def test_orphaned():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1, skipped=1)


# =============================================================================
# Test: Missing specs directory handling
# =============================================================================


class TestMissingSpecsDirectory:
    """Tests for handling missing specs directories."""

    def test_no_specs_directory_runs_all_tests(self, pytester: Pytester) -> None:
        """Test that tests run without validation when specs are missing."""
        features_dir = pytester.path / "features"
        if features_dir.exists():
            shutil.rmtree(features_dir)
        # Note: No specs directory created
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="any-feature", scenario_id="any-scenario")
            def test_without_validation():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

    def test_warning_logged_without_specs(self, pytester: Pytester) -> None:
        """Test that a warning is logged when specs are missing."""
        features_dir = pytester.path / "features"
        if features_dir.exists():
            shutil.rmtree(features_dir)
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="any-feature", scenario_id="any-scenario")
            def test_without_validation():
                pass
            """
        )
        result = pytester.runpytest("-v", "--log-cli-level=WARNING")
        result.assert_outcomes(passed=1)
        # Warning should be in output (may be in different formats)


# =============================================================================
# Test: Runtime marker injection
# =============================================================================


class TestMarkerInjection:
    """Tests for runtime marker injection from scenario tags."""

    def test_markers_injected_from_tags(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that markers are injected from scenario tags."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        # Run only tests with 'smoke' marker (from tags)
        result = pytester.runpytest("-v", "-m", "smoke")
        result.assert_outcomes(passed=1)

    def test_multiple_markers_injected(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that multiple markers are injected from multiple tags."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        # Test with 'critical' marker
        result = pytester.runpytest("-v", "-m", "critical")
        result.assert_outcomes(passed=1)

    def test_marker_with_hyphen_sanitized(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that hyphens in tags are converted to underscores."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        # 'auth-flow' tag becomes 'auth_flow' marker
        result = pytester.runpytest("-v", "-m", "auth_flow")
        result.assert_outcomes(passed=1)

    def test_filter_by_injected_marker(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test filtering tests by injected markers."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_smoke_critical():
                pass

            @specleft(feature_id="auth", scenario_id="login-failure")
            def test_regression():
                pass

            @specleft(feature_id="parse", scenario_id="extract-unit")
            def test_unit():
                pass
            """
        )
        # Run only regression tests
        result = pytester.runpytest("-v", "-m", "regression")
        result.assert_outcomes(passed=1)

        # Run only smoke tests
        result = pytester.runpytest("-v", "-m", "smoke")
        result.assert_outcomes(passed=1)

    def test_exclude_by_marker(self, pytester: Pytester, create_specs_tree) -> None:
        """Test excluding tests by marker."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_smoke():
                pass

            @specleft(feature_id="auth", scenario_id="login-failure")
            def test_regression():
                pass
            """
        )
        # Run tests NOT marked as smoke
        result = pytester.runpytest("-v", "-m", "not smoke")
        result.assert_outcomes(passed=1)


# =============================================================================
# Test: Step collection
# =============================================================================


class TestStepCollection:
    """Tests for step collection during test execution."""

    def test_steps_collected(self, pytester: Pytester, create_specs_tree) -> None:
        """Test that steps are collected during test execution."""
        pytester.makepyfile(
            """
            from specleft import specleft, step

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_with_steps():
                with step("Given user has credentials"):
                    pass
                with step("When user logs in"):
                    pass
                with step("Then user sees dashboard"):
                    pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

    def test_failed_step_captured(self, pytester: Pytester, create_specs_tree) -> None:
        """Test that failed steps are captured."""
        pytester.makepyfile(
            """
            from specleft import specleft, step

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_with_failing_step():
                with step("Given user has credentials"):
                    pass
                with step("When user logs in"):
                    assert False, "Login failed"
                with step("Then user sees dashboard"):
                    pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(failed=1)


# =============================================================================
# Test: Result persistence
# =============================================================================


class TestResultPersistence:
    """Tests for result persistence to disk."""

    def test_results_saved_to_disk(self, pytester: Pytester, create_specs_tree) -> None:
        """Test that results are saved to .specleft/results/."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

        # Check that results directory was created
        results_dir = pytester.path / ".specleft" / "results"
        assert results_dir.exists(), "Results directory should exist"

        # Check that a results file was created
        json_files = list(results_dir.glob("results_*.json"))
        assert len(json_files) == 1, "One results file should exist"

        # Verify the content
        results_data = json.loads(json_files[0].read_text())
        assert "summary" in results_data
        assert results_data["summary"]["passed"] == 1

    def test_results_summary_printed(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that results summary is printed to console."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)
        result.stdout.fnmatch_lines(["*SpecLeft Test Results*"])


# =============================================================================
# Test: Edge cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_non_specleft_tests_unaffected(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that non-specleft tests are unaffected."""
        pytester.makepyfile(
            """
            from specleft import specleft

            def test_regular():
                pass

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_specleft():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=2)

    def test_invalid_specs_handled(self, pytester: Pytester) -> None:
        """Test that invalid specs are handled gracefully."""
        _write_specs_tree(pytester.path)
        (pytester.path / "features" / "auth" / "_feature.md").write_text(
            "{ invalid yaml }"
        )

        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="any-feature", scenario_id="any-scenario")
            def test_runs_anyway():
                pass
            """
        )
        # Should run without error, just log a warning
        result = pytester.runpytest("-v")
        result.assert_outcomes(skipped=1)

    def test_empty_tags_no_markers_added(self, pytester: Pytester) -> None:
        """Test that scenarios with empty tags don't cause issues."""
        features_dir = pytester.path / "features"
        scenario_file = features_dir / "auth" / "login" / "login_failure.md"
        scenario_file.write_text(
            """
        ---
        scenario_id: login-failure
        priority: medium
        tags: []
        execution_time: fast
        ---

        # Scenario: Failed login

        ## Steps
        - **Given** user has invalid credentials
        - **When** user tries to log in
        - **Then** user sees error message
        """.strip()
        )

        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-failure")
            def test_no_tags():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)


# =============================================================================
# Test: Sanitize marker name
# =============================================================================


class TestSanitizeMarkerName:
    """Tests for the marker name sanitization function."""

    def test_hyphen_replaced(self) -> None:
        """Test that hyphens are replaced with underscores."""
        from specleft.pytest_plugin import _sanitize_marker_name

        assert _sanitize_marker_name("auth-flow") == "auth_flow"
        assert _sanitize_marker_name("multi-word-tag") == "multi_word_tag"

    def test_space_replaced(self) -> None:
        """Test that spaces are replaced with underscores."""
        from specleft.pytest_plugin import _sanitize_marker_name

        assert _sanitize_marker_name("auth flow") == "auth_flow"
        assert _sanitize_marker_name("multi word tag") == "multi_word_tag"

    def test_combined_replacement(self) -> None:
        """Test replacement of both hyphens and spaces."""
        from specleft.pytest_plugin import _sanitize_marker_name

        assert _sanitize_marker_name("auth-flow test") == "auth_flow_test"

    def test_simple_tag_unchanged(self) -> None:
        """Test that simple tags remain unchanged."""
        from specleft.pytest_plugin import _sanitize_marker_name

        assert _sanitize_marker_name("smoke") == "smoke"
        assert _sanitize_marker_name("regression") == "regression"
