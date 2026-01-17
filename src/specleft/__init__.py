"""SpecLeft - Specification-driven test management for pytest."""

from specleft.decorators import StepResult, reusable_step, specleft, step
from specleft.schema import (
    ExecutionTime,
    FeatureSpec,
    Priority,
    ScenarioSpec,
    SpecDataRow,
    SpecStep,
    SpecsConfig,
    StepType,
    StorySpec,
)
from specleft.spec_differ import SpecDiffer, StepDiff
from specleft.skeleton_revisor import RevisionPlan, TestFunctionRevisor

__version__ = "0.2.0"
__all__ = [
    "ExecutionTime",
    "FeatureSpec",
    "Priority",
    "ScenarioSpec",
    "SpecDataRow",
    "SpecStep",
    "SpecsConfig",
    "RevisionPlan",
    "SpecDiffer",
    "StepDiff",
    "StepResult",
    "StepType",
    "StorySpec",
    "TestFunctionRevisor",
    "reusable_step",
    "specleft",
    "step",
]
