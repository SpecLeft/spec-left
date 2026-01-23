"""Tests for the pytest plugin functionality.

Tests cover:
- Hook execution order
- Metadata collection from @specleft decorated tests
- Runtime marker injection from tags
- Thread-local storage handling
- Handling of missing specs
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.helpers.specs import write_specs_tree

if TYPE_CHECKING:
    from pytest import Pytester


@pytest.fixture
def create_specs_tree(pytester: Pytester) -> Path:
    """Create a Markdown specs tree in the test directory."""
    return write_specs_tree(pytester.path)


@pytest.fixture(autouse=True)
def ensure_specs_tree(create_specs_tree: Path) -> None:
    """Ensure a default specs tree exists for plugin tests."""
    _ = create_specs_tree


class TestPytestConfigure:
    """Tests for pytest_configure hook."""

    def test_specleft_results_initialized(self, pytester: Pytester) -> None:
        """Test that _specleft_results is initialized on config."""
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_dummy():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

    def test_metadata_stored_on_item(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that metadata is stored on test items."""
        pytester.makeconftest("""
            def pytest_runtest_setup(item):
                if hasattr(item, '_specleft_metadata'):
                    metadata = item._specleft_metadata
                    assert metadata['feature_id'] == 'auth'
                    assert metadata['scenario_id'] == 'login-success'
            """)
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """)
        result = pytester.runpytest()
        result.assert_outcomes(passed=1)


class TestMissingSpecsDirectory:
    """Tests for handling missing specs directories."""

    def test_no_specs_directory_runs_all_tests(self, pytester: Pytester) -> None:
        """Test that tests run without validation when specs are missing."""
        features_dir = pytester.path / "features"
        if features_dir.exists():
            for path in features_dir.rglob("*"):
                if path.is_file():
                    path.unlink()
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="any-feature", scenario_id="any-scenario")
            def test_without_validation():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

    def test_metadata_defaults_when_no_specs(self, pytester: Pytester) -> None:
        """Test metadata defaults when specs are missing."""
        features_dir = pytester.path / "features"
        if features_dir.exists():
            for path in features_dir.rglob("*"):
                if path.is_file():
                    path.unlink()

        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="any-feature", scenario_id="any-scenario")
            def test_without_metadata():
                pass
            """)
        pytester.makeconftest("""
            def pytest_runtest_call(item):
                metadata = item._specleft_metadata
                assert metadata.get('feature_name') is None
                assert metadata.get('scenario_name') is None
                assert metadata.get('tags') == []
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)


class TestMarkerInjection:
    """Tests for runtime marker injection from scenario tags."""

    def test_markers_injected_from_tags(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that markers are injected from scenario tags."""
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """)
        pytester.makeconftest("""
            def pytest_collection_modifyitems(session, config, items):
                for item in items:
                    if hasattr(item, '_specleft_metadata'):
                        metadata = item._specleft_metadata
                        assert metadata['feature_name'] == 'User Authentication'
                        assert metadata['scenario_name'] == 'Successful login'
                        assert 'smoke' in metadata['tags']
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-tag", "smoke")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-tag", "critical")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-tag", "missing")
        result.assert_outcomes(skipped=1)

    def test_priority_marker_injected(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that priority markers are injected from spec priority."""
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-priority", "high")
        result.assert_outcomes(passed=1)

        result = pytester.runpytest("-v", "--specleft-priority", "critical")
        result.assert_outcomes(skipped=1)


class TestStepCollection:
    """Tests for step collection during test execution."""

    def test_steps_collected(self, pytester: Pytester, create_specs_tree) -> None:
        """Test that steps are collected during test execution."""
        pytester.makepyfile("""
            from specleft import specleft, step

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_with_steps():
                with step("Given user has credentials"):
                    pass
                with step("When user logs in"):
                    pass
                with step("Then user sees dashboard"):
                    pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)


class TestResultPersistence:
    """Tests for result persistence to disk."""

    def test_results_saved_to_disk(self, pytester: Pytester, create_specs_tree) -> None:
        """Test that results are saved to .specleft/results/."""
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

        results_dir = pytester.path / ".specleft" / "results"
        assert results_dir.exists(), "Results directory should exist"

        json_files = list(results_dir.glob("results_*.json"))
        assert len(json_files) == 1, "One results file should exist"

        results_data = json.loads(json_files[0].read_text())
        assert "summary" in results_data
        assert results_data["summary"]["passed"] == 1
        assert results_data["features"][0]["feature_name"] == "User Authentication"
        assert (
            results_data["features"][0]["scenarios"][0]["scenario_name"]
            == "Successful login"
        )


class TestSanitizeMarkerName:
    """Tests for marker name sanitization."""

    def test_hyphen_replaced(self) -> None:
        """Test that hyphens are replaced with underscores."""
        from specleft.pytest_plugin import _sanitize_marker_name

        assert _sanitize_marker_name("auth-flow") == "auth_flow"


class TestCollectAllTags:
    """Tests for collecting all tags from specs."""

    def test_collects_tags_from_all_scenarios(self) -> None:
        """Test that all unique tags are collected from specs."""
        from specleft.pytest_plugin import _collect_all_tags
        from specleft.schema import (
            FeatureSpec,
            Priority,
            ScenarioSpec,
            SpecsConfig,
            StorySpec,
        )

        specs_config = SpecsConfig(
            features=[
                FeatureSpec(
                    feature_id="auth",
                    name="Auth",
                    stories=[
                        StorySpec(
                            story_id="login",
                            name="Login",
                            scenarios=[
                                ScenarioSpec(
                                    scenario_id="login-success",
                                    name="Successful login",
                                    priority=Priority.HIGH,
                                    tags=["smoke", "critical"],
                                ),
                                ScenarioSpec(
                                    scenario_id="login-failure",
                                    name="Failed login",
                                    priority=Priority.MEDIUM,
                                    tags=["regression", "negative"],
                                ),
                            ],
                        ),
                    ],
                ),
                FeatureSpec(
                    feature_id="parse",
                    name="Parsing",
                    stories=[
                        StorySpec(
                            story_id="units",
                            name="Units",
                            scenarios=[
                                ScenarioSpec(
                                    scenario_id="extract-unit",
                                    name="Extract unit",
                                    priority=Priority.MEDIUM,
                                    tags=["unit", "smoke"],  # "smoke" is duplicate
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        tags = _collect_all_tags(specs_config)

        assert tags == {"smoke", "critical", "regression", "negative", "unit"}

    def test_returns_empty_set_when_no_tags(self) -> None:
        """Test that empty set is returned when scenarios have no tags."""
        from specleft.pytest_plugin import _collect_all_tags
        from specleft.schema import (
            FeatureSpec,
            ScenarioSpec,
            SpecsConfig,
            StorySpec,
        )

        specs_config = SpecsConfig(
            features=[
                FeatureSpec(
                    feature_id="auth",
                    name="Auth",
                    stories=[
                        StorySpec(
                            story_id="login",
                            name="Login",
                            scenarios=[
                                ScenarioSpec(
                                    scenario_id="login-success",
                                    name="Successful login",
                                    tags=[],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

        tags = _collect_all_tags(specs_config)

        assert tags == set()


class TestDynamicMarkerRegistration:
    """Tests for dynamic marker registration from scenario tags."""

    def test_no_unknown_marker_warnings(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that no PytestUnknownMarkWarning is raised for scenario tags."""
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """)
        # Run with -W error to turn warnings into errors
        result = pytester.runpytest(
            "-v", "-W", "error::pytest.PytestUnknownMarkWarning"
        )
        result.assert_outcomes(passed=1)
        # Should not contain any unknown marker warnings
        assert "PytestUnknownMarkWarning" not in result.stdout.str()

    def test_markers_registered_for_all_priorities(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that priority markers are registered dynamically."""
        pytester.makepyfile("""
            import pytest
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_high_priority():
                pass

            @specleft(feature_id="auth", scenario_id="login-failure")
            def test_medium_priority():
                pass
            """)
        # Run with strict markers and turn warnings to errors
        result = pytester.runpytest(
            "-v",
            "--strict-markers",
            "-W",
            "error::pytest.PytestUnknownMarkWarning",
        )
        result.assert_outcomes(passed=2)

    def test_hyphenated_tags_registered_correctly(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that hyphenated tags are sanitized and registered."""
        # The specs tree includes "auth-flow" tag which should become "auth_flow"
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_with_hyphenated_tag():
                pass
            """)
        result = pytester.runpytest(
            "-v",
            "--strict-markers",
            "-W",
            "error::pytest.PytestUnknownMarkWarning",
        )
        result.assert_outcomes(passed=1)


class TestSkippedTestCapture:
    """Tests for capturing skipped tests in results."""

    def test_skipped_tests_captured_in_results(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that skipped tests are captured in results JSON."""
        pytester.makepyfile("""
            import pytest
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success", skip=True)
            def test_skipped():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(skipped=1)

        results_dir = pytester.path / ".specleft" / "results"
        json_files = list(results_dir.glob("results_*.json"))
        assert len(json_files) == 1

        results_data = json.loads(json_files[0].read_text())
        assert results_data["summary"]["skipped"] == 1
        assert results_data["summary"]["total_executions"] == 1

    def test_skipped_via_pytest_mark_captured(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that tests skipped via pytest.mark.skip are captured."""
        pytester.makepyfile("""
            import pytest
            from specleft import specleft

            @pytest.mark.skip(reason="Not implemented yet")
            @specleft(feature_id="auth", scenario_id="login-success")
            def test_skipped_by_marker():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(skipped=1)

        results_dir = pytester.path / ".specleft" / "results"
        json_files = list(results_dir.glob("results_*.json"))
        assert len(json_files) == 1

        results_data = json.loads(json_files[0].read_text())
        assert results_data["summary"]["skipped"] == 1

    def test_mixed_passed_and_skipped_results(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that both passed and skipped tests are captured correctly."""
        pytester.makepyfile("""
            import pytest
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_passed():
                pass

            @specleft(feature_id="auth", scenario_id="login-failure", skip=True)
            def test_skipped():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1, skipped=1)

        results_dir = pytester.path / ".specleft" / "results"
        json_files = list(results_dir.glob("results_*.json"))
        results_data = json.loads(json_files[0].read_text())

        assert results_data["summary"]["passed"] == 1
        assert results_data["summary"]["skipped"] == 1
        assert results_data["summary"]["total_executions"] == 2


class TestTagsInMetadata:
    """Tests for tags being included in test metadata."""

    def test_tags_included_in_results(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that scenario tags are included in results JSON."""
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_with_tags():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

        results_dir = pytester.path / ".specleft" / "results"
        json_files = list(results_dir.glob("results_*.json"))
        results_data = json.loads(json_files[0].read_text())

        execution = results_data["features"][0]["scenarios"][0]["executions"][0]
        assert "tags" in execution
        # login-success has tags: [smoke, critical, auth-flow]
        assert "smoke" in execution["tags"]
        assert "critical" in execution["tags"]
        assert "auth-flow" in execution["tags"]

    def test_empty_tags_when_no_scenario_tags(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that empty tags list is included when scenario has no tags."""
        # Create a scenario without tags
        scenario_dir = pytester.path / "features" / "notags" / "story"
        scenario_dir.mkdir(parents=True)

        (pytester.path / "features" / "notags" / "_feature.md").write_text("""
---
feature_id: notags
priority: medium
---

# Feature: No Tags Feature
""".strip())
        (scenario_dir / "_story.md").write_text("""
---
story_id: story
priority: medium
---

# Story: Story
""".strip())
        (scenario_dir / "no_tags.md").write_text("""
---
scenario_id: no-tags
priority: medium
tags: []
---

# Scenario: No tags scenario
""".strip())

        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="notags", scenario_id="no-tags")
            def test_no_tags():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)

        results_dir = pytester.path / ".specleft" / "results"
        json_files = list(results_dir.glob("results_*.json"))
        results_data = json.loads(json_files[0].read_text())

        # Find the notags feature
        notags_feature = next(
            f for f in results_data["features"] if f["feature_id"] == "notags"
        )
        execution = notags_feature["scenarios"][0]["executions"][0]
        assert "tags" in execution
        assert execution["tags"] == []


class TestFilterBehavior:
    """Tests for SpecLeft filter handling."""

    def test_filters_skip_without_specs(self, pytester: Pytester) -> None:
        """Test that filters skip tests when specs are missing."""
        features_dir = pytester.path / "features"
        if features_dir.exists():
            for path in features_dir.rglob("*"):
                if path.is_file():
                    path.unlink()
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_filtered():
                pass
            """)
        result = pytester.runpytest("-v", "--specleft-tag", "smoke")
        result.assert_outcomes(skipped=1)

    def test_filters_skip_when_tag_missing(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that tag filters skip non-matching scenarios."""
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_filtered():
                pass
            """)
        result = pytester.runpytest("-v", "--specleft-tag", "missing")
        result.assert_outcomes(skipped=1)

    def test_filters_allow_matching_priority(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that priority filters keep matching scenarios."""
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_high():
                pass
            """)
        result = pytester.runpytest("-v", "--specleft-priority", "high")
        result.assert_outcomes(passed=1)

    def test_filters_skip_unknown_scenario(
        self, pytester: Pytester, create_specs_tree
    ) -> None:
        """Test that unknown scenarios are skipped when specs exist."""
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="unknown")
            def test_unknown():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(skipped=1)

    def test_load_specs_config_uses_rootpath(self, pytester: Pytester) -> None:
        """Test that specs are found via config rootpath."""
        features_dir = pytester.path / "features"
        story_dir = features_dir / "auth" / "login"
        story_dir.mkdir(parents=True, exist_ok=True)
        (features_dir / "auth" / "_feature.md").write_text("""
---
feature_id: auth
---

# Feature: Auth
""".strip())
        (story_dir / "_story.md").write_text("""
---
story_id: login
---

# Story: Login
""".strip())
        (story_dir / "login_success.md").write_text("""
---
scenario_id: login-success
---

# Scenario: Login Success
""".strip())
        pytester.makepyfile("""
            from specleft import specleft

            @specleft(feature_id="auth", scenario_id="login-success")
            def test_login():
                pass
            """)
        result = pytester.runpytest("-v")
        result.assert_outcomes(passed=1)
