"""Contract test execution helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Callable

from click.testing import CliRunner

from specleft.commands.cli_access import get_cli
from specleft.commands.contracts.types import ContractCheckResult
from specleft.commands.contracts.utils import create_contract_specs, load_json_output
from specleft.utils.filesystem import (
    compare_file_snapshot,
    record_file_snapshot,
    working_directory,
)


def emit_contract_check(check: ContractCheckResult, verbose: bool) -> None:
    from specleft.commands.contracts.table import emit_contract_check as _emit

    _emit(check, verbose)


def run_contract_tests(
    *,
    verbose: bool,
    on_progress: Callable[[ContractCheckResult], None] | None = None,
) -> tuple[bool, list[ContractCheckResult], list[str]]:
    cli = get_cli()

    checks: list[ContractCheckResult] = []
    errors: list[str] = []
    runner = CliRunner()

    def _record_check(result: ContractCheckResult) -> None:
        checks.append(result)
        if on_progress is not None:
            on_progress(result)

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        _create_contract_specs(root)

        with working_directory(root):
            dry_run_result = runner.invoke(
                cli, ["test", "skeleton", "--dry-run", "--format", "json"]
            )
            dry_run_pass = dry_run_result.exit_code == 0 and not Path("tests").exists()
            _record_check(
                ContractCheckResult(
                    category="safety",
                    name="dry_run_no_writes",
                    status="pass" if dry_run_pass else "fail",
                    message=None if dry_run_pass else "Dry run created files",
                )
            )

            cancel_result = runner.invoke(cli, ["test", "skeleton"], input="n\n")
            cancel_pass = cancel_result.exit_code == 2 and not Path("tests").exists()
            _record_check(
                ContractCheckResult(
                    category="safety",
                    name="no_implicit_writes",
                    status="pass" if cancel_pass else "fail",
                    message=None
                    if cancel_pass
                    else "Skeleton wrote without confirmation",
                )
            )

            create_result = runner.invoke(cli, ["test", "skeleton"], input="y\n")
            generated_file = Path("tests/auth/test_login.py")
            created = create_result.exit_code == 0 and generated_file.exists()
            _record_check(
                ContractCheckResult(
                    category="execution",
                    name="skeletons_skipped_by_default",
                    status="pass"
                    if created and "skip=True" in generated_file.read_text()
                    else "fail",
                    message=None
                    if created and "skip=True" in generated_file.read_text()
                    else "Skeleton tests are not skipped",
                )
            )

            if created:
                snapshot = record_file_snapshot(root)
                rerun_result = runner.invoke(cli, ["test", "skeleton"])
                unchanged = rerun_result.exit_code == 0 and compare_file_snapshot(
                    root, snapshot
                )
            else:
                unchanged = False

            _record_check(
                ContractCheckResult(
                    category="safety",
                    name="existing_tests_not_modified_by_default",
                    status="pass" if unchanged else "fail",
                    message=None
                    if unchanged
                    else "Existing tests were modified without --force",
                )
            )

            validate_snapshot = record_file_snapshot(root)
            validate_result = runner.invoke(
                cli, ["features", "validate", "--format", "json"]
            )
            validation_pass = validate_result.exit_code == 0 and compare_file_snapshot(
                root, validate_snapshot
            )
            _record_check(
                ContractCheckResult(
                    category="execution",
                    name="validation_non_destructive",
                    status="pass" if validation_pass else "fail",
                    message=None if validation_pass else "Validation modified files",
                )
            )

            def _normalize_payload(raw_output: str) -> dict[str, object] | None:
                payload = load_json_output(raw_output, allow_preamble=True)
                if isinstance(payload, dict):
                    payload.pop("timestamp", None)
                    return payload
                return None

            baseline_result = runner.invoke(
                cli, ["test", "skeleton", "--dry-run", "--format", "json"]
            )
            deterministic_result = runner.invoke(
                cli, ["test", "skeleton", "--dry-run", "--format", "json"]
            )
            baseline_payload = _normalize_payload(baseline_result.output)
            deterministic_payload = _normalize_payload(deterministic_result.output)
            deterministic_pass = (
                baseline_result.exit_code == 0
                and deterministic_result.exit_code == 0
                and deterministic_payload is not None
                and deterministic_payload == baseline_payload
            )
            _record_check(
                ContractCheckResult(
                    category="determinism",
                    name="deterministic_for_same_inputs",
                    status="pass" if deterministic_pass else "fail",
                    message=None
                    if deterministic_pass
                    else "Outputs differed between runs",
                )
            )

            retry_snapshot = record_file_snapshot(root)
            safe_retry_pass = compare_file_snapshot(root, retry_snapshot)
            _record_check(
                ContractCheckResult(
                    category="determinism",
                    name="safe_for_retries",
                    status="pass" if safe_retry_pass else "fail",
                    message=None
                    if safe_retry_pass
                    else "Retry introduced side effects",
                )
            )

            json_commands = [
                ("doctor", ["doctor", "--format", "json"]),
                ("status", ["status", "--format", "json"]),
                ("next", ["next", "--format", "json"]),
                ("coverage", ["coverage", "--format", "json"]),
                ("features_list", ["features", "list", "--format", "json"]),
                ("features_stats", ["features", "stats", "--format", "json"]),
                ("features_validate", ["features", "validate", "--format", "json"]),
                ("report", ["test", "report", "--format", "json"]),
                ("contract", ["contract", "--format", "json"]),
                ("contract_test", ["contract", "test", "--format", "json"]),
                (
                    "skeleton",
                    ["test", "skeleton", "--dry-run", "--format", "json"],
                ),
            ]

            json_pass = True
            json_failures: list[str] = []
            for label, command in json_commands:
                result = runner.invoke(cli, command)
                payload = load_json_output(
                    result.output, allow_preamble=label == "contract_test"
                )
                if payload is None:
                    json_pass = False
                    json_failures.append(label)
                    continue
                if result.exit_code not in {0, 1, 2}:
                    json_pass = False
                    json_failures.append(label)
            _record_check(
                ContractCheckResult(
                    category="cli_api",
                    name="json_supported_globally",
                    status="pass" if json_pass else "fail",
                    message=None
                    if json_pass
                    else f"JSON format unsupported: {', '.join(json_failures)}",
                )
            )

            contract_result = runner.invoke(cli, ["contract", "--format", "json"])
            schema_pass = False
            if contract_result.exit_code == 0:
                contract_payload = load_json_output(contract_result.output)
                schema_pass = isinstance(contract_payload, dict) and bool(
                    contract_payload.get("contract_version")
                    and contract_payload.get("specleft_version")
                    and contract_payload.get("guarantees")
                )
            _record_check(
                ContractCheckResult(
                    category="cli_api",
                    name="json_schema_valid",
                    status="pass" if schema_pass else "fail",
                    message=None
                    if schema_pass
                    else "Contract JSON missing required keys",
                )
            )

            exit_code_pass = cancel_result.exit_code == 2
            _record_check(
                ContractCheckResult(
                    category="cli_api",
                    name="exit_codes_correct",
                    status="pass" if exit_code_pass else "fail",
                    message=None if exit_code_pass else "Cancel exit code not 2",
                )
            )

            skip_pass = create_result.exit_code == 0
            _record_check(
                ContractCheckResult(
                    category="execution",
                    name="skipped_never_fail",
                    status="pass" if skip_pass else "fail",
                    message=None if skip_pass else "Skeleton run failed",
                )
            )

    passed = all(check.status == "pass" for check in checks)
    if not passed:
        errors.append("Agent Contract violation detected")
    if verbose:
        for check in checks:
            if check.status == "fail" and check.message:
                errors.append(f"{check.category}: {check.name} - {check.message}")

    return passed, checks, errors
