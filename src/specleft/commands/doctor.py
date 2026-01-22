"""Doctor command."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import click

from specleft.commands.constants import CLI_VERSION


def _load_dependency_names() -> list[str]:
    dependencies = ["pytest", "pydantic", "click", "jinja2", "python-frontmatter"]
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return dependencies

    try:
        content = pyproject_path.read_text()
    except OSError:
        return dependencies

    match = re.search(
        r"^\s*dependencies\s*=\s*\[(.*?)\]\s*$", content, re.DOTALL | re.MULTILINE
    )
    if not match:
        return dependencies

    dependencies_block = match.group(1)
    entries = re.findall(r'"([^"]+)"', dependencies_block)
    parsed: list[str] = []
    for entry in entries:
        name = re.split(r"[<>=\s]", entry.strip(), maxsplit=1)[0]
        if name:
            parsed.append(name)

    return parsed or dependencies


def _build_doctor_checks() -> dict[str, Any]:
    import importlib.metadata as metadata

    cli_check = {"status": "pass", "version": CLI_VERSION}

    python_info = sys.version_info
    minimum_python = (3, 9, 0)
    python_version = f"{python_info.major}.{python_info.minor}.{python_info.micro}"
    python_ok = python_info >= minimum_python
    python_check = {
        "status": "pass" if python_ok else "fail",
        "version": python_version,
        "minimum": "3.9.0",
    }
    if not python_ok:
        python_check["message"] = f"Python 3.9+ required. Current: {python_version}"

    dependencies = _load_dependency_names()
    dependency_packages: list[dict[str, object]] = []
    dependencies_ok = True
    for package in dependencies:
        try:
            dependency_packages.append(
                {
                    "name": package,
                    "version": metadata.version(package),
                    "status": "pass",
                }
            )
        except metadata.PackageNotFoundError:
            dependency_packages.append(
                {
                    "name": package,
                    "version": None,
                    "status": "fail",
                    "message": "Not installed",
                }
            )
            dependencies_ok = False

    dependency_check = {
        "status": "pass" if dependencies_ok else "fail",
        "packages": dependency_packages,
    }

    plugin_registered = False
    plugin_status = "fail"
    plugin_error = None
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            output = result.stdout + result.stderr
            plugin_registered = "specleft" in output.lower()
            plugin_status = "pass" if plugin_registered else "warn"
        else:
            plugin_status = "fail"
            plugin_error = result.stderr.strip() or "pytest execution failed"
    except Exception as exc:
        plugin_status = "fail"
        plugin_error = str(exc)

    plugin_check: dict[str, object] = {
        "status": plugin_status,
        "registered": plugin_registered,
    }
    if plugin_error:
        plugin_check["error"] = plugin_error

    features_dir = Path("features")
    tests_dir = Path("tests")
    features_readable = features_dir.exists() and os.access(features_dir, os.R_OK)
    tests_writable = tests_dir.exists() and os.access(tests_dir, os.W_OK)
    if not tests_dir.exists():
        tests_writable = os.access(Path("."), os.W_OK)
    directories_ok = (features_readable or not features_dir.exists()) and tests_writable
    directory_status = "pass" if directories_ok else "warn"

    directory_check = {
        "status": directory_status,
        "features_readable": features_readable,
        "tests_writable": tests_writable,
    }

    return {
        "version": CLI_VERSION,
        "checks": {
            "cli_available": cli_check,
            "pytest_plugin": plugin_check,
            "python_version": python_check,
            "dependencies": dependency_check,
            "directories": directory_check,
        },
    }


def _build_doctor_output(checks: dict[str, Any]) -> dict[str, Any]:
    checks_map = cast(dict[str, Any], checks.get("checks", {}))
    errors: list[str] = []
    suggestions: list[str] = []
    healthy = True

    python_check = checks_map.get("python_version", {})
    if python_check.get("status") == "fail":
        healthy = False
        errors.append(
            f"Python version {python_check.get('version')} is below minimum {python_check.get('minimum')}"
        )
        suggestions.append("Upgrade Python: pyenv install 3.11")

    dependencies_check = checks_map.get("dependencies", {})
    if dependencies_check.get("status") != "pass":
        healthy = False
        for package in dependencies_check.get("packages", []):
            if package.get("status") == "fail":
                name = package.get("name")
                errors.append(f"Missing required package: {name}")
                suggestions.append(f"Install {name}: pip install {name}")

    if checks_map.get("pytest_plugin", {}).get("status") == "fail":
        healthy = False
        errors.append("Pytest plugin registration check failed")
        suggestions.append("Ensure SpecLeft is installed: pip install -e .")

    if checks_map.get("directories", {}).get("status") != "pass":
        healthy = False
        errors.append("Feature/test directory access issue")
        suggestions.append("Check directory permissions")

    output = {
        "healthy": healthy,
        "version": checks.get("version"),
        "timestamp": datetime.now().isoformat(),
        "checks": checks_map,
    }

    if errors:
        output["errors"] = errors
    if suggestions:
        output["suggestions"] = suggestions

    return output


def _print_doctor_table(checks: dict[str, Any], *, verbose: bool) -> None:
    checks_map = cast(dict[str, Any], checks.get("checks", {}))
    click.echo("Checking SpecLeft installation...")
    cli_check = checks_map.get("cli_available", {})
    click.echo(f"✓ specleft CLI available (version {cli_check.get('version')})")

    plugin_check = checks_map.get("pytest_plugin", {})
    if plugin_check.get("status") == "pass":
        click.echo("✓ pytest plugin registered")
    elif plugin_check.get("status") == "warn":
        click.echo("⚠ pytest plugin may not be registered")
    else:
        click.echo("✗ pytest plugin check failed")

    python_check = checks_map.get("python_version", {})
    python_marker = "✓" if python_check.get("status") == "pass" else "✗"
    click.echo(
        f"{python_marker} Python version compatible ({python_check.get('version')})"
    )

    dependencies_check = checks_map.get("dependencies", {})
    dependencies_marker = "✓" if dependencies_check.get("status") == "pass" else "✗"
    click.echo(f"{dependencies_marker} All dependencies installed")
    for package in dependencies_check.get("packages", []):
        marker = "✓" if package.get("status") == "pass" else "✗"
        version = package.get("version") or "not installed"
        click.echo(f"  - {package.get('name')} ({version}) {marker}")
        if verbose and package.get("message"):
            click.echo(f"    {package.get('message')}")

    directory_check = checks_map.get("directories", {})
    features_marker = "✓" if directory_check.get("features_readable") else "✗"
    tests_marker = "✓" if directory_check.get("tests_writable") else "✗"
    click.echo(f"{features_marker} Can read feature directory (features/)")
    click.echo(f"{tests_marker} Can write to test directory (tests/)")

    if verbose and plugin_check.get("error"):
        click.echo(f"pytest plugin error: {plugin_check.get('error')}")

    if checks.get("errors"):
        click.echo("")
        click.secho("Issues detected:", fg="red")
        for error in checks.get("errors", []):
            click.echo(f"  - {error}")
        if checks.get("suggestions"):
            click.echo("")
            click.secho("Suggestions:", fg="yellow")
            for suggestion in checks.get("suggestions", []):
                click.echo(f"  - {suggestion}")
    else:
        click.echo("")
        click.echo("SpecLeft is ready to use.")


@click.command("doctor")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    show_default=True,
    help="Output format: 'table' or 'json'.",
)
@click.option("--verbose", is_flag=True, help="Show detailed diagnostic information.")
def doctor(format_type: str, verbose: bool) -> None:
    """Verify SpecLeft installation and environment."""
    checks = _build_doctor_checks()
    output = _build_doctor_output(checks)

    if format_type == "json":
        click.echo(json.dumps(output, indent=2))
    else:
        _print_doctor_table(output, verbose=verbose)

    sys.exit(0 if output.get("healthy") else 1)
