"""Payload builders for contract commands."""

from __future__ import annotations

from specleft.commands.contracts.types import ContractCheckResult
from specleft.commands.constants import CLI_VERSION, CONTRACT_DOC_PATH, CONTRACT_VERSION


def build_contract_payload() -> dict[str, object]:
    return {
        "contract_version": CONTRACT_VERSION,
        "specleft_version": CLI_VERSION,
        "guarantees": {
            "safety": {
                "no_implicit_writes": True,
                "dry_run_never_writes": True,
                "existing_tests_not_modified_by_default": True,
            },
            "execution": {
                "skeletons_skipped_by_default": True,
                "skipped_never_fail": True,
                "validation_non_destructive": True,
            },
            "determinism": {
                "deterministic_for_same_inputs": True,
                "safe_for_retries": True,
            },
            "cli_api": {
                "json_supported_globally": True,
                "json_additive_within_minor": True,
                "exit_codes": {
                    "success": 0,
                    "error": 1,
                    "cancelled": 2,
                },
            },
        },
        "docs": {
            "agent_contract": CONTRACT_DOC_PATH,
        },
    }


def build_contract_test_payload(
    *,
    passed: bool,
    checks: list[ContractCheckResult],
    errors: list[str],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "contract_version": CONTRACT_VERSION,
        "specleft_version": CLI_VERSION,
        "passed": passed,
        "checks": [
            {
                "category": check.category,
                "name": check.name,
                "status": check.status,
                **({"message": check.message} if check.message else {}),
            }
            for check in checks
        ],
    }
    if errors:
        payload["errors"] = errors
    return payload
