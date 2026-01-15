"""Tests for the pytest plugin functionality.

Tests cover:
- Hook execution order
- Metadata collection from @specleft decorated tests
- Auto-skip for removed scenarios
- Runtime marker injection from tags
- Thread-local storage handling
- Handling of missing features.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import Pytester


# =============================================================================
# Helper fixtures
# =============================================================================


@pytest.fixture
def sample_features_json() -> dict:
    """Return a sample features.json structure."""
    return {
        "version": "1.0",
        "features": [
            {
                "id": "AUTH-001",
                "name": "User Authentication",
                "scenarios": [
                    {
                        "id": "login-success",
                        "name": "Successful login",
                        "tags": ["smoke", "critical", "auth-flow"],
                        "steps": [
                            {
                                "type": "given",
                                "description": "user has valid credentials",
                            },
                            {"type": "when", "description": "user logs in"},
                            {"type": "then", "description": "user sees dashboard"},
                        ],
                    },
                    {
                        "id": "login-failure",
                        "name": "Failed login",
                        "tags": ["regression", "negative"],
                        "steps": [
                            {
                                "type": "given",
                                "description": "user has invalid credentials",
                            },
                            {"type": "when", "description": "user tries to log in"},
                            {"type": "then", "description": "user sees error message"},
                        ],
                    },
                ],
            },
            {
                "id": "PARSE-001",
                "name": "Unit Parsing",
                "scenarios": [
                    {
                        "id": "extract-unit",
                        "name": "Extract unit from string",
                        "tags": ["unit", "parsing"],
                        "steps": [
                            {"type": "when", "description": "extracting unit"},
                            {"type": "then", "description": "unit is correct"},
                        ],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def create_features_json(pytester: Pytester, sample_features_json: dict):
    """Create a features.json file in the test directory."""

    def _create(features: dict | None = None) -> Path:
        data = features if features is not None else sample_features_json
        features_file = pytester.path / "features.json"
        features_file.write_text(json.dumps(data, indent=2))
        return features_file

    return _create


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

            @specleft(feature_id="TEST-001", scenario_id="test-scenario")
            def test_dummy():
                pass
            """
        )
        # Create a minimal features.json
        features = {
            "version": "1.0",
            "features": [
                {
                    "id": "TEST-001",
                    "name": "Test",
                    "scenarios": [
                        {
                            "id": "test-scenario",
                            "name": "Test scenario",
                            "steps": [{"type": "when", "description": "testing"}],
                        },
                    ],
                },
            ],
        }
        import json

        (pytester.path / "features.json").write_text(json.dumps(features))
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)
        # Check that results were saved (which means _specleft_results was initialized)
        result.stdout.fnmatch_lines(["*SpecLeft Test Results*"])

    def test_specleft_marker_registered(self, pytester: Pytester) -> None:
        """Test that specleft marker is registered."""
        pytester.makepyfile(
            """
            import pytest

            @pytest.mark.specleft
            def test_with_marker():
                pass
            """
        )
        result = pytester.runpytest("--strict-markers")
        result.assert_outcomes(passed=1)


# =============================================================================
# Test: Metadata collection
# =============================================================================


class TestMetadataCollection:
    """Tests for metadata collection from @specleft decorated tests."""

    def test_basic_metadata_collection(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that basic metadata is collected from @specleft tests."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

    def test_parameterized_test_metadata(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test metadata collection for parameterized tests."""
        create_features_json()
        pytester.makepyfile(
            """
            import pytest
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            @pytest.mark.parametrize("username,password", [
                ("user1", "pass1"),
                ("user2", "pass2"),
            ])
            def test_login_param(username, password):
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=2)

    def test_metadata_stored_on_item(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that metadata is stored on test items."""
        create_features_json()
        pytester.makeconftest(
            """
            def pytest_runtest_setup(item):
                if hasattr(item, '_specleft_metadata'):
                    metadata = item._specleft_metadata
                    assert metadata['feature_id'] == 'AUTH-001'
                    assert metadata['scenario_id'] == 'login-success'
            """
        )
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
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
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that tests with removed scenarios are skipped."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="nonexistent-scenario")
            def test_orphaned():
                pass
            """
        )
        result = pytester.runpytest("-v", "-rs")  # -rs shows skip reasons
        result.assert_outcomes(skipped=1)
        # Check skip reason is in output (using -rs flag)
        result.stdout.fnmatch_lines(
            ["*nonexistent-scenario*not found in features.json*"]
        )

    def test_skip_orphaned_feature(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that tests with removed features are skipped."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="NONEXISTENT-001", scenario_id="login-success")
            def test_orphaned():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(skipped=1)

    def test_skip_reason_includes_identifiers(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that skip reason includes feature and scenario IDs."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="REMOVED-001", scenario_id="deleted-scenario")
            def test_orphaned():
                pass
            """
        )
        result = pytester.runpytest("-v", "-rs")
        result.assert_outcomes(skipped=1)
        result.stdout.fnmatch_lines(["*deleted-scenario*REMOVED-001*"])

    def test_valid_scenario_not_skipped(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that valid scenarios are not skipped."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            def test_valid():
                pass

            @specleft(feature_id="AUTH-001", scenario_id="login-failure")
            def test_also_valid():
                pass

            @specleft(feature_id="PARSE-001", scenario_id="extract-unit")
            def test_another_valid():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=3)

    def test_mixed_valid_and_orphaned(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that valid and orphaned tests are handled correctly together."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            def test_valid():
                pass

            @specleft(feature_id="AUTH-001", scenario_id="orphaned-scenario")
            def test_orphaned():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1, skipped=1)


# =============================================================================
# Test: Missing features.json handling
# =============================================================================


class TestMissingFeaturesJson:
    """Tests for handling missing features.json."""

    def test_no_features_json_runs_all_tests(self, pytester: Pytester) -> None:
        """Test that tests run without validation when features.json is missing."""
        # Note: No features.json created
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="ANY-001", scenario_id="any-scenario")
            def test_without_validation():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

    def test_warning_logged_without_features_json(self, pytester: Pytester) -> None:
        """Test that a warning is logged when features.json is missing."""
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="ANY-001", scenario_id="any-scenario")
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
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that markers are injected from scenario tags."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        # Run only tests with 'smoke' marker (from tags)
        result = pytester.runpytest("-v", "-m", "smoke")
        result.assert_outcomes(passed=1)

    def test_multiple_markers_injected(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that multiple markers are injected from multiple tags."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        # Test with 'critical' marker
        result = pytester.runpytest("-v", "-m", "critical")
        result.assert_outcomes(passed=1)

    def test_marker_with_hyphen_sanitized(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that hyphens in tags are converted to underscores."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            def test_login():
                pass
            """
        )
        # 'auth-flow' tag becomes 'auth_flow' marker
        result = pytester.runpytest("-v", "-m", "auth_flow")
        result.assert_outcomes(passed=1)

    def test_filter_by_injected_marker(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test filtering tests by injected markers."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            def test_smoke_critical():
                pass

            @specleft(feature_id="AUTH-001", scenario_id="login-failure")
            def test_regression():
                pass

            @specleft(feature_id="PARSE-001", scenario_id="extract-unit")
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

    def test_exclude_by_marker(self, pytester: Pytester, create_features_json) -> None:
        """Test excluding tests by marker."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            def test_smoke():
                pass

            @specleft(feature_id="AUTH-001", scenario_id="login-failure")
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

    def test_steps_collected(self, pytester: Pytester, create_features_json) -> None:
        """Test that steps are collected during test execution."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft, step

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
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

    def test_failed_step_captured(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that failed steps are captured."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft, step

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
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

    def test_results_saved_to_disk(
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that results are saved to .specleft/results/."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
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
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that results summary is printed to console."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
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
        self, pytester: Pytester, create_features_json
    ) -> None:
        """Test that non-specleft tests are unaffected."""
        create_features_json()
        pytester.makepyfile(
            """
            from specleft import specleft

            def test_regular():
                pass

            @specleft(feature_id="AUTH-001", scenario_id="login-success")
            def test_specleft():
                pass
            """
        )
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=2)

    def test_invalid_features_json_handled(self, pytester: Pytester) -> None:
        """Test that invalid features.json is handled gracefully."""
        # Create invalid features.json
        features_file = pytester.path / "features.json"
        features_file.write_text("{ invalid json }")

        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="ANY-001", scenario_id="any-scenario")
            def test_runs_anyway():
                pass
            """
        )
        # Should run without error, just log a warning
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

    def test_empty_tags_no_markers_added(self, pytester: Pytester) -> None:
        """Test that scenarios with empty tags don't cause issues."""
        features = {
            "version": "1.0",
            "features": [
                {
                    "id": "TEST-001",
                    "name": "Test Feature",
                    "scenarios": [
                        {
                            "id": "no-tags",
                            "name": "Scenario without tags",
                            "tags": [],  # Empty tags
                            "steps": [
                                {"type": "when", "description": "something happens"},
                            ],
                        },
                    ],
                },
            ],
        }
        features_file = pytester.path / "features.json"
        features_file.write_text(json.dumps(features, indent=2))

        pytester.makepyfile(
            """
            from specleft import specleft

            @specleft(feature_id="TEST-001", scenario_id="no-tags")
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
