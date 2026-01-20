# SpecLeft for AI Agents

This guide is optimized for AI agents (like Claude Code, GitHub Copilot Workspace, Aider, Cursor, etc.) that want to adopt SpecLeft for test specification and generation in Python projects.

## Table of Contents
- [Quick Evaluation](#quick-evaluation)
- [Installation & Verification](#installation--verification)
- [Common Workflows](#common-workflows)
- [Programmatic API](#programmatic-api)
- [Common Patterns](#common-patterns)
- [Error Handling](#error-handling)
- [Tips for Agents](#tips-for-agents)

---

## Quick Evaluation

### Why SpecLeft Works Well for AI Agents

SpecLeft exposes:
- explicit system state
- explicit missing work
- explicit intent boundaries

Unlike codegen tools:
- it does not infer behaviour
- it does not mutate tests
- it does not guess correctness

This makes SpecLeft suitable for:
- autonomous planning
- incremental execution
- safe retries

### When to Use SpecLeft

Use SpecLeft if the project:
- ✅ Already uses pytest
- ✅ Has features/behaviors that map to business requirements
- ✅ Needs visibility into test coverage by feature
- ✅ Wants structured test scaffolding
- ✅ Has acceptance criteria or user stories to track

Skip SpecLeft if:
- ❌ Only writing ad-hoc unit tests for internal functions
- ❌ Tests don't map to user-facing features or behaviors
- ❌ No need for specification tracking or coverage visibility
- ❌ Project uses a different test framework (not pytest)

### Decision Checklist

```python
def should_use_specleft(project_dir: Path) -> dict:
    """Evaluate if SpecLeft is appropriate for this project."""
    
    checks = {
        "uses_pytest": False,
        "has_requirements": False,
        "needs_coverage_tracking": False,
        "recommendation": "skip"
    }
    
    # Check if pytest is used
    checks["uses_pytest"] = (
        (project_dir / "pytest.ini").exists() or
        (project_dir / "pyproject.toml").exists() and 
        "pytest" in (project_dir / "pyproject.toml").read_text()
    )
    
    # Check if there are features/stories to track
    checks["has_requirements"] = (
        (project_dir / "docs").exists() or
        (project_dir / "requirements").exists() or
        len(list(project_dir.glob("**/stories/*.md"))) > 0 or
        len(list(project_dir.glob("**/PRD*.md"))) > 0
    )
    
    # Check if project has multiple features
    src_dirs = list(project_dir.glob("src/**/")) or list(project_dir.glob("app/**/"))
    checks["needs_coverage_tracking"] = len(src_dirs) > 3
    
    # Make recommendation
    if checks["uses_pytest"] and checks["has_requirements"]:
        checks["recommendation"] = "use"
    elif checks["uses_pytest"] and checks["needs_coverage_tracking"]:
        checks["recommendation"] = "consider"
    else:
        checks["recommendation"] = "skip"
    
    return checks
```

---

## Installation & Verification

### Step 1: Install SpecLeft

```python
import subprocess

def install_specleft():
    """Install SpecLeft package."""
    result = subprocess.run(
        ["pip", "install", "specleft"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Installation failed: {result.stderr}")
    
    return True
```

### Step 2: Verify Installation

```python
import json
import subprocess

def verify_specleft_installation():
    """Verify SpecLeft is properly installed."""
    try:
        result = subprocess.run(
            ["specleft", "doctor", "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        
        health = json.loads(result.stdout)
        
        if not health["healthy"]:
            print("SpecLeft installation has issues:")
            for error in health.get("errors", []):
                print(f"  - {error}")
            return False
        
        print(f"✓ SpecLeft {health['version']} is ready")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"SpecLeft not properly installed: {e.stderr}")
        return False
    except json.JSONDecodeError:
        print("Could not parse SpecLeft doctor output")
        return False
```

### Step 3: Check Project Compatibility

```python
def check_project_status():
    """Check current state of project tests."""
    result = subprocess.run(
        ["specleft", "features", "stats", "--format", "json"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
```

---

## Common Workflows

### Workflow 1: Initialize SpecLeft in New Project

**Use Case:** Starting fresh with SpecLeft

```python
import subprocess
import json
from pathlib import Path

def initialize_specleft_project():
    """Initialize SpecLeft with example specs."""
    
    # 1. Review agent contract
    contract_result = subprocess.run(
        ["specleft", "contract", "--format", "json"],
        capture_output=True,
        text=True
    )
    contract = json.loads(contract_result.stdout)
    print(f"✓ Contract version {contract['version']}")

    # 2. Check project fit
    stats_result = subprocess.run(
        ["specleft", "features", "stats", "--format", "json"],
        capture_output=True,
        text=True
    )
    stats = json.loads(stats_result.stdout)
    print(f"✓ Found {stats['summary']['features']} features")

    # 3. Preview example structure
    preview_result = subprocess.run(
        ["specleft", "init", "--example", "--dry-run", "--format", "json"],
        capture_output=True,
        text=True
    )
    preview = json.loads(preview_result.stdout)
    print(f"✓ Would create {preview['summary']['files']} files")

    # 4. Create example structure
    result = subprocess.run(
        ["specleft", "init", "--example"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Init failed: {result.stderr}")

    print("✓ Example project created")

    # 5. Validate the example
    result = subprocess.run(
        ["specleft", "features", "validate", "--format", "json"],
        capture_output=True,
        text=True
    )

    validation = json.loads(result.stdout)

    if not validation["valid"]:
        print("Example validation failed:")
        for error in validation["errors"]:
            print(f"  {error['file']}: {error['message']}")
        return False

    print(f"✓ Example validated ({validation['scenarios']} scenarios)")

    # 6. Preview what tests would be created
    result = subprocess.run(
        ["specleft", "test", "skeleton", "--dry-run", "--format", "json"],
        capture_output=True,
        text=True
    )

    plan = json.loads(result.stdout)
    print(f"✓ Would create {len(plan['would_create'])} test files")

    # 7. Generate test skeletons
    result = subprocess.run(
        ["specleft", "test", "skeleton"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Skeleton generation failed: {result.stderr}")

    print("✓ Test skeletons generated")

    return True
```

---

### Workflow 2: Generate Specs from Requirements Document

**Use Case:** You have a PRD or requirements document and want to create feature specs

```python
import json
import subprocess
from pathlib import Path
from typing import List, Dict

def extract_features_from_prd(prd_content: str) -> List[Dict]:
    """
    Extract features from requirements document.
    This is where you would use your LLM to parse requirements.
    """
    # Your LLM logic here to extract:
    # - Feature ID, name, description
    # - Stories within each feature
    # - Scenarios for each story
    # - Steps for each scenario
    
    # Example return structure:
    return [
        {
            "feature_id": "auth",
            "name": "User Authentication",
            "description": "User registration, login, and session management",
            "priority": "high",
            "tags": ["security", "user-management"],
            "stories": [
                {
                    "story_id": "login",
                    "name": "User Login",
                    "description": "Authenticate users with credentials",
                    "priority": "critical",
                    "scenarios": [
                        {
                            "scenario_id": "successful-login",
                            "name": "Successful login with valid credentials",
                            "priority": "critical",
                            "tags": ["smoke", "authentication"],
                            "steps": [
                                {"type": "given", "description": "user has valid credentials"},
                                {"type": "when", "description": "user attempts to login"},
                                {"type": "then", "description": "user is authenticated"},
                                {"type": "and", "description": "session token is returned"}
                            ]
                        },
                        {
                            "scenario_id": "invalid-credentials",
                            "name": "Login fails with invalid credentials",
                            "priority": "high",
                            "tags": ["authentication", "error-handling"],
                            "steps": [
                                {"type": "given", "description": "user has invalid credentials"},
                                {"type": "when", "description": "user attempts to login"},
                                {"type": "then", "description": "login is rejected"},
                                {"type": "and", "description": "error message is shown"}
                            ]
                        }
                    ]
                }
            ]
        }
    ]

def create_spec_files(features: List[Dict], base_dir: Path = Path("features")):
    """Create SpecLeft specification files from extracted features."""
    
    for feature in features:
        feature_dir = base_dir / feature["feature_id"]
        feature_dir.mkdir(parents=True, exist_ok=True)
        
        # Create _feature.md
        feature_content = f"""---
feature_id: {feature["feature_id"]}
priority: {feature.get("priority", "medium")}
tags: {feature.get("tags", [])}
---

# Feature: {feature["name"]}

{feature.get("description", "")}
"""
        (feature_dir / "_feature.md").write_text(feature_content)
        
        # Create stories and scenarios
        for story in feature["stories"]:
            story_dir = feature_dir / story["story_id"]
            story_dir.mkdir(exist_ok=True)
            
            # Create _story.md
            story_content = f"""---
story_id: {story["story_id"]}
priority: {story.get("priority", "medium")}
---

# Story: {story["name"]}

{story.get("description", "")}
"""
            (story_dir / "_story.md").write_text(story_content)
            
            # Create scenario files
            for scenario in story["scenarios"]:
                scenario_file = story_dir / f"{scenario['scenario_id']}.md"
                
                # Format steps
                steps_text = "\n".join([
                    f"- **{step['type'].capitalize()}** {step['description']}"
                    for step in scenario["steps"]
                ])
                
                scenario_content = f"""---
scenario_id: {scenario["scenario_id"]}
priority: {scenario.get("priority", "medium")}
tags: {scenario.get("tags", [])}
---

# Scenario: {scenario["name"]}

## Steps
{steps_text}
"""
                scenario_file.write_text(scenario_content)
    
    print(f"✓ Created {len(features)} features with specs")

def workflow_prd_to_specs(prd_file: Path):
    """Complete workflow: PRD → Specs → Validation → Test Generation"""
    
    # 1. Read PRD
    prd_content = prd_file.read_text()
    print(f"Reading PRD: {prd_file}")
    
    # 2. Extract features (using your LLM)
    features = extract_features_from_prd(prd_content)
    print(f"✓ Extracted {len(features)} features")
    
    # 3. Create spec files
    create_spec_files(features)
    
    # 4. Validate specs
    result = subprocess.run(
        ["specleft", "features", "validate", "--format", "json"],
        capture_output=True,
        text=True
    )
    
    validation = json.loads(result.stdout)
    
    if not validation["valid"]:
        print("❌ Validation failed:")
        for error in validation["errors"]:
            print(f"  {error['file']}: {error['message']}")
            print(f"    Suggestion: {error.get('suggestion', 'N/A')}")
        return False
    
    print(f"✓ Specs validated: {validation['scenarios']} scenarios")
    
    # 5. Generate skeleton tests
    result = subprocess.run(
        ["specleft", "test", "skeleton"],
        capture_output=True,
        text=True
    )
    
    print("✓ Test skeletons generated")
    
    # 6. Check status
    result = subprocess.run(
        ["specleft", "status", "--format", "json"],
        capture_output=True,
        text=True
    )
    
    status = json.loads(result.stdout)
    print(f"Coverage: {status['summary']['coverage_percent']}% (0% expected for new specs)")
    
    return True
```

---

### Workflow 3: Implement Tests Iteratively

**Use Case:** Generate tests one at a time, implement, verify, repeat

```python
import subprocess
import json
from pathlib import Path

def get_next_test_to_implement():
    """Get the next test that needs implementation."""
    result = subprocess.run(
        ["specleft", "next", "--limit", "1", "--format", "json"],
        capture_output=True,
        text=True
    )
    
    data = json.loads(result.stdout)
    
    if not data["tests"]:
        return None  # All tests implemented
    
    return data["tests"][0]

def implement_test(test_info: dict, test_implementation: str):
    """
    Implement a test by replacing the skeleton with actual logic.
    
    Args:
        test_info: Test information from specleft next
        test_implementation: Full test code (with skip=False)
    """
    test_file = Path(test_info["test_file"])
    
    # Write the implementation
    test_file.write_text(test_implementation)
    
    print(f"✓ Implemented {test_info['scenario_id']}")

def verify_test(test_info: dict) -> bool:
    """Run the test to verify it passes."""
    result = subprocess.run(
        ["pytest", test_info["test_file"], "-v"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✓ Test passed: {test_info['scenario_id']}")
        return True
    else:
        print(f"❌ Test failed: {test_info['scenario_id']}")
        print(result.stdout)
        return False

def generate_test_implementation(test_info: dict) -> str:
    """
    Generate test implementation code.
    This is where you would use your LLM to generate the test logic.
    
    Args:
        test_info: Test information from specleft next
        
    Returns:
        Complete test file content
    """
    # Read the spec file to understand requirements
    spec_content = Path(test_info["spec_file"]).read_text()
    
    # Your LLM logic here to generate test implementation
    # The key is to:
    # 1. Remove skip=True from the decorator
    # 2. Replace 'pass' with actual test logic
    # 3. Use appropriate fixtures/setup
    
    # Example generated code:
    return f'''"""
Test for {test_info['scenario_name']}
Generated from: {test_info['spec_file']}
"""
import pytest
from specleft import specleft

@specleft(
    feature_id="{test_info['feature_id']}",
    scenario_id="{test_info['scenario_id']}"
)
def {test_info['test_function']}(app_client):
    """{test_info['scenario_name']}"""
    
    # Implementation based on steps:
    {generate_step_implementations(test_info['steps'])}
'''

def generate_step_implementations(steps: list) -> str:
    """Generate code for each step (LLM logic here)."""
    # Your implementation logic
    pass

def workflow_implement_all_tests():
    """Iteratively implement all unimplemented tests."""
    
    implemented_count = 0
    failed_count = 0
    
    while True:
        # Get next test to implement
        test_info = get_next_test_to_implement()
        
        if not test_info:
            print("✅ All tests implemented!")
            break
        
        print(f"\nImplementing: {test_info['feature_id']}/{test_info['scenario_id']}")
        print(f"  Priority: {test_info['priority']}")
        print(f"  Steps: {test_info['step_count']}")
        
        # Generate implementation (using LLM)
        implementation = generate_test_implementation(test_info)
        
        # Write implementation
        implement_test(test_info, implementation)
        
        # Verify it works
        if verify_test(test_info):
            implemented_count += 1
        else:
            failed_count += 1
            print("  ⚠️  Test failed, continuing to next...")
            # In production, you might want to retry or debug
        
        # Show progress
        result = subprocess.run(
            ["specleft", "status", "--format", "json"],
            capture_output=True,
            text=True
        )
        status = json.loads(result.stdout)
        print(f"  Coverage: {status['summary']['coverage_percent']}%")
    
    print(f"\n✓ Implemented: {implemented_count}")
    print(f"❌ Failed: {failed_count}")
    
    # Final coverage report
    subprocess.run(["specleft", "test", "report", "--open-browser"])
```

---

### Workflow 4: Add SpecLeft to Existing Test Suite

**Use Case:** Project already has tests, want to add feature tracking

```python
import subprocess
import json
from pathlib import Path

def analyze_existing_tests():
    """Analyze existing test suite."""
    result = subprocess.run(
        ["pytest", "--collect-only", "-q"],
        capture_output=True,
        text=True
    )
    
    # Parse output to count tests
    lines = result.stdout.split('\n')
    test_count = len([l for l in lines if '::test_' in l])
    
    print(f"Found {test_count} existing tests")
    return test_count

def create_specs_for_existing_tests(test_files: list):
    """
    Create feature specs by analyzing existing test files.
    This is reverse engineering: tests → specs
    """
    # Your logic to:
    # 1. Parse test files
    # 2. Group by feature/story
    # 3. Extract test intent from docstrings/names
    # 4. Create spec files
    
    # Example structure detection:
    # tests/auth/test_login.py → features/auth/login/
    # tests/calculator/test_add.py → features/calculator/addition/
    
    pass

def workflow_retrofit_existing_tests():
    """Add SpecLeft to existing test suite."""
    
    # 1. Analyze what exists
    test_count = analyze_existing_tests()
    
    # 2. Create specs based on existing tests
    test_files = list(Path("tests").rglob("test_*.py"))
    create_specs_for_existing_tests(test_files)
    
    # 3. Validate specs
    result = subprocess.run(
        ["specleft", "features", "validate", "--format", "json"],
        capture_output=True,
        text=True
    )
    
    validation = json.loads(result.stdout)
    print(f"Created {validation['scenarios']} scenarios from existing tests")
    
    # 4. Update existing tests to use @specleft decorator
    # (This would be your LLM logic to modify test files)
    
    # 5. Check coverage
    result = subprocess.run(
        ["specleft", "status", "--format", "json"],
        capture_output=True,
        text=True
    )
    
    status = json.loads(result.stdout)
    print(f"Initial coverage: {status['summary']['coverage_percent']}%")
```

---

## Programmatic API

All SpecLeft commands support `--format json` for programmatic access. Use `specleft init --dry-run --format json` for non-interactive init previews and `specleft contract --format json` for contract metadata.

### Core Helper Functions

```python
import subprocess
import json
from typing import Optional, List, Dict
from pathlib import Path

class SpecLeftAPI:
    """Programmatic interface to SpecLeft CLI."""
    
    @staticmethod
    def doctor() -> dict:
        """Check SpecLeft installation health."""
        result = subprocess.run(
            ["specleft", "doctor", "--format", "json"],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)
    
    @staticmethod
    def status(
        features_dir: str = "features",
        feature_id: Optional[str] = None,
        story_id: Optional[str] = None,
        unimplemented: bool = False
    ) -> dict:
        """Get implementation status."""
        cmd = ["specleft", "status", "--format", "json", "--dir", features_dir]
        
        if feature_id:
            cmd.extend(["--feature", feature_id])
        if story_id:
            cmd.extend(["--story", story_id])
        if unimplemented:
            cmd.append("--unimplemented")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)
    
    @staticmethod
    def next_tests(
        limit: int = 5,
        priority: Optional[str] = None,
        feature_id: Optional[str] = None
    ) -> List[dict]:
        """Get next tests to implement."""
        cmd = ["specleft", "next", "--format", "json", "--limit", str(limit)]
        
        if priority:
            cmd.extend(["--priority", priority])
        if feature_id:
            cmd.extend(["--feature", feature_id])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return data.get("tests", [])
    
    @staticmethod
    def validate(features_dir: str = "features") -> dict:
        """Validate feature specifications."""
        result = subprocess.run(
            ["specleft", "features", "validate", "--format", "json", "--dir", features_dir],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)
    
    @staticmethod
    def coverage(threshold: Optional[int] = None) -> dict:
        """Get coverage metrics."""
        cmd = ["specleft", "coverage", "--format", "json"]
        
        if threshold:
            cmd.extend(["--threshold", str(threshold)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout)
    
    @staticmethod
    def skeleton_preview() -> dict:
        """Preview skeleton test generation."""
        result = subprocess.run(
            ["specleft", "test", "skeleton", "--dry-run", "--format", "json"],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)

    @staticmethod
    def contract() -> dict:
        """Fetch the SpecLeft Agent Contract."""
        result = subprocess.run(
            ["specleft", "contract", "--format", "json"],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout)
    
    @staticmethod
    def skeleton_generate(confirm: bool = True) -> bool:
        """Generate skeleton tests."""
        if confirm:
            # Interactive confirmation
            result = subprocess.run(
                ["specleft", "test", "skeleton"],
                input="y\n",
                capture_output=True,
                text=True
            )
        else:
            # Force generation
            result = subprocess.run(
                ["specleft", "test", "skeleton", "--force"],
                capture_output=True,
                text=True
            )
        
        return result.returncode == 0
```

### Usage Examples

```python
# Check health
api = SpecLeftAPI()
health = api.doctor()
if not health["healthy"]:
    print("SpecLeft not ready:", health["errors"])

# Get coverage
coverage = api.coverage()
print(f"Coverage: {coverage['coverage']['overall']['percent']}%")

# Get next test to implement
tests = api.next_tests(limit=1)
if tests:
    next_test = tests[0]
    print(f"Next: {next_test['feature_id']}/{next_test['scenario_id']}")
    print(f"  File: {next_test['test_file']}")

# Validate specs
validation = api.validate()
if not validation["valid"]:
    for error in validation["errors"]:
        print(f"Error in {error['file']}: {error['message']}")

# Check if coverage meets threshold
coverage = api.coverage(threshold=80)
# Will raise error if below 80%
```

---

## Common Patterns

### Pattern 1: Check Before Acting

Always verify SpecLeft is appropriate before proceeding:

```python
def safe_specleft_adoption(project_dir: Path):
    """Safely adopt SpecLeft with validation."""
    
    # 1. Check if appropriate
    evaluation = should_use_specleft(project_dir)
    
    if evaluation["recommendation"] == "skip":
        print("SpecLeft not recommended for this project")
        return False
    
    # 2. Install
    install_specleft()
    
    # 3. Verify installation
    if not verify_specleft_installation():
        print("Installation verification failed")
        return False
    
    # 4. Preview init plan
    preview = subprocess.run(
        ["specleft", "init", "--example", "--dry-run", "--format", "json"],
        capture_output=True,
        text=True,
    )
    print(json.loads(preview.stdout))
    
    # 5. Initialize
    result = subprocess.run(["specleft", "init", "--example"])
    
    # 6. Validate
    api = SpecLeftAPI()
    validation = api.validate()
    
    if not validation["valid"]:
        print("Initial validation failed")
        return False
    
    return True
```

### Pattern 2: Iterative Implementation with Error Handling

```python
def implement_with_retries(max_retries: int = 3):
    """Implement tests with retry logic."""
    
    api = SpecLeftAPI()
    
    while True:
        tests = api.next_tests(limit=1)
        
        if not tests:
            break  # All done
        
        test_info = tests[0]
        
        for attempt in range(max_retries):
            try:
                # Generate implementation
                impl = generate_test_implementation(test_info)
                
                # Write file
                Path(test_info["test_file"]).write_text(impl)
                
                # Verify
                result = subprocess.run(
                    ["pytest", test_info["test_file"], "-v"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    print(f"✓ {test_info['scenario_id']}")
                    break  # Success
                else:
                    if attempt < max_retries - 1:
                        print(f"  Retry {attempt + 1}/{max_retries}")
                        # Adjust implementation based on error
                    else:
                        print(f"❌ Failed after {max_retries} attempts")
                        
            except Exception as e:
                print(f"Error: {e}")
                if attempt >= max_retries - 1:
                    print(f"❌ Skipping {test_info['scenario_id']}")
```

### Pattern 3: CI Integration

```python
def ci_coverage_check(threshold: int = 80):
    """Check coverage in CI pipeline."""
    
    api = SpecLeftAPI()
    
    # Get current coverage
    coverage = api.coverage()
    current = coverage["coverage"]["overall"]["percent"]
    
    print(f"Feature Coverage: {current}%")
    
    if current < threshold:
        print(f"❌ Coverage {current}% below threshold {threshold}%")
        
        # Show what needs implementing
        tests = api.next_tests(limit=10)
        print(f"\n{len(tests)} tests need implementation:")
        for test in tests[:5]:
            print(f"  - {test['feature_id']}/{test['scenario_id']} ({test['priority']})")
        
        return False
    
    print(f"✓ Coverage meets threshold")
    return True
```

### Pattern 4: Spec Generation from Code Comments

```python
import ast
from pathlib import Path

def extract_scenario_from_test_docstring(test_func_ast):
    """Extract scenario from test function docstring."""
    docstring = ast.get_docstring(test_func_ast)
    
    if not docstring:
        return None
    
    # Parse docstring for Given/When/Then
    steps = []
    for line in docstring.split('\n'):
        line = line.strip()
        if line.startswith('Given'):
            steps.append({"type": "given", "description": line[6:]})
        elif line.startswith('When'):
            steps.append({"type": "when", "description": line[5:]})
        elif line.startswith('Then'):
            steps.append({"type": "then", "description": line[5:]})
    
    return steps if steps else None

def generate_spec_from_test_file(test_file: Path):
    """Generate SpecLeft spec from existing test file."""
    
    # Parse test file
    tree = ast.parse(test_file.read_text())
    
    scenarios = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            steps = extract_scenario_from_test_docstring(node)
            
            if steps:
                scenario_id = node.name.replace('test_', '').replace('_', '-')
                scenarios.append({
                    "scenario_id": scenario_id,
                    "name": node.name.replace('test_', '').replace('_', ' ').title(),
                    "steps": steps
                })
    
    return scenarios
```

---

## Error Handling

### Handle Common Errors Gracefully

```python
class SpecLeftError(Exception):
    """Base exception for SpecLeft operations."""
    pass

class ValidationError(SpecLeftError):
    """Spec validation failed."""
    pass

class InstallationError(SpecLeftError):
    """SpecLeft installation issue."""
    pass

def safe_specleft_call(command: list, expect_json: bool = False):
    """Safely call SpecLeft CLI with error handling."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        
        if expect_json:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                raise SpecLeftError(f"Invalid JSON output: {e}")
        
        return result.stdout
        
    except subprocess.CalledProcessError as e:
        raise SpecLeftError(f"Command failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise SpecLeftError("Command timed out")
    except FileNotFoundError:
        raise InstallationError("SpecLeft not installed")

# Usage
try:
    status = safe_specleft_call(
        ["specleft", "status", "--format", "json"],
        expect_json=True
    )
except InstallationError:
    print("Please install SpecLeft: pip install specleft")
except SpecLeftError as e:
    print(f"SpecLeft error: {e}")
```

### Validate Before Proceeding

```python
def validate_before_generation():
    """Always validate specs before generating tests."""
    
    try:
        validation = safe_specleft_call(
            ["specleft", "features", "validate", "--format", "json"],
            expect_json=True
        )
    except SpecLeftError as e:
        print(f"Cannot validate: {e}")
        return False
    
    if not validation["valid"]:
        print("❌ Specs have errors:")
        for error in validation["errors"]:
            print(f"\n{error['file']}:{error.get('line', '?')}")
            print(f"  {error['message']}")
            if "suggestion" in error:
                print(f"  Suggestion: {error['suggestion']}")
        
        return False
    
    if validation.get("warnings"):
        print("⚠️  Specs have warnings:")
        for warning in validation["warnings"]:
            print(f"  {warning['file']}: {warning['message']}")
    
    print(f"✓ Specs valid ({validation['scenarios']} scenarios)")
    return True
```

---

## Tips for Agents

### 1. Always Verify Installation First

```python
# Before doing anything else:
api = SpecLeftAPI()
health = api.doctor()

if not health["healthy"]:
    print("SpecLeft not ready. Issues:")
    for check_name, check_data in health["checks"].items():
        if check_data["status"] != "pass":
            print(f"  - {check_name}: {check_data.get('message', 'Failed')}")
    exit(1)
```

### 2. Use Dry Run Before Generating

```python
# Always preview before creating files
preview = api.skeleton_preview()

print(f"Will create {len(preview['would_create'])} files:")
for item in preview["would_create"][:5]:  # Show first 5
    print(f"  - {item['test_file']} ({item['steps']} steps)")

# Ask user or auto-confirm based on preview
if len(preview["would_create"]) > 0:
    api.skeleton_generate(confirm=True)
```

### 3. Track Progress and Show User

```python
def show_progress():
    """Show user current progress."""
    api = SpecLeftAPI()
    
    status = api.status()
    summary = status["summary"]
    
    print(f"\nProgress Report:")
    print(f"  Features: {summary['total_features']}")
    print(f"  Scenarios: {summary['total_scenarios']}")
    print(f"  Implemented: {summary['implemented']}/{summary['total_scenarios']}")
    print(f"  Coverage: {summary['coverage_percent']}%")
    
    if summary["skipped"] > 0:
        tests = api.next_tests(limit=3)
        print(f"\nNext to implement:")
        for test in tests:
            print(f"  - {test['feature_id']}/{test['scenario_id']} ({test['priority']})")
```

### 4. Handle Spec Validation Errors Gracefully

```python
def fix_validation_errors():
    """Attempt to auto-fix common validation errors."""
    
    validation = api.validate()
    
    if not validation["valid"]:
        for error in validation["errors"]:
            # Example: Fix scenario_id format
            if "must be lowercase kebab-case" in error["message"]:
                # Read file, fix YAML frontmatter, write back
                fix_kebab_case_error(error["file"], error["field"])
        
        # Re-validate
        validation = api.validate()
        
    return validation["valid"]
```

### 5. Use Priority Filtering

```python
# Implement high-priority tests first
high_priority = api.next_tests(priority="high", limit=10)

for test in high_priority:
    implement_test(test)

# Then medium priority
medium_priority = api.next_tests(priority="medium", limit=10)
```

### 6. Integrate with CI/CD

```python
# In CI pipeline
def ci_workflow():
    """Run SpecLeft checks in CI."""
    
    # 1. Validate specs
    validation = api.validate()
    if not validation["valid"]:
        print("::error::Spec validation failed")
        exit(1)
    
    # 2. Check coverage
    coverage = api.coverage(threshold=70)
    
    # 3. Run tests
    result = subprocess.run(["pytest", "-v"])
    
    if result.returncode != 0:
        print("::error::Tests failed")
        exit(1)
    
    # 4. Generate report
    subprocess.run(["specleft", "test", "report", "--output", "coverage-report.html"])
```

### 7. Graceful Degradation

```python
def try_specleft_or_fallback():
    """Try to use SpecLeft, fall back to regular pytest if not available."""
    
    try:
        health = api.doctor()
        if health["healthy"]:
            # Use SpecLeft workflow
            return use_specleft_workflow()
    except Exception as e:
        print(f"SpecLeft not available: {e}")
    
    # Fall back to regular pytest
    print("Falling back to regular pytest workflow")
    return use_regular_pytest_workflow()
```

---

## Complete Example: End-to-End Agent Workflow

```python
#!/usr/bin/env python3
"""
Complete example: AI agent adopting SpecLeft for a Python project.
"""

import subprocess
import json
from pathlib import Path
from typing import Optional

class SpecLeftAgent:
    """AI Agent that uses SpecLeft for test management."""
    
    def __init__(self):
        self.api = SpecLeftAPI()
    
    def setup_project(self, project_dir: Path) -> bool:
        """Set up SpecLeft in a project."""
        
        print("🤖 Setting up SpecLeft...")
        
        # 1. Evaluate if appropriate
        evaluation = should_use_specleft(project_dir)
        
        if evaluation["recommendation"] == "skip":
            print("❌ SpecLeft not recommended for this project")
            print(f"  Reasons: {evaluation}")
            return False
        
        print(f"✓ SpecLeft recommended ({evaluation['recommendation']})")
        
        # 2. Install
        print("\n📦 Installing SpecLeft...")
        install_specleft()
        
        # 3. Verify
        health = self.api.doctor()
        if not health["healthy"]:
            print("❌ Installation issues:")
            for error in health.get("errors", []):
                print(f"  - {error}")
            return False
        
        print(f"✓ SpecLeft {health['version']} ready")
        
        return True
    
    def create_specs_from_requirements(self, prd_file: Path):
        """Create feature specs from requirements."""
        
        print(f"\n📝 Processing requirements from {prd_file}...")
        
        # Extract features (your LLM logic)
        prd_content = prd_file.read_text()
        features = extract_features_from_prd(prd_content)
        
        print(f"✓ Extracted {len(features)} features")
        
        # Create spec files
        create_spec_files(features)
        
        # Validate
        validation = self.api.validate()
        
        if not validation["valid"]:
            print("❌ Validation errors:")
            for error in validation["errors"]:
                print(f"  {error['file']}: {error['message']}")
            return False
        
        print(f"✓ Created {validation['scenarios']} scenarios")
        
        return True
    
    def generate_and_implement_tests(self):
        """Generate skeletons and implement all tests."""
        
        print("\n🧪 Generating test skeletons...")
        
        # Preview
        preview = self.api.skeleton_preview()
        print(f"Will create {len(preview['would_create'])} test files")
        
        # Generate
        self.api.skeleton_generate(confirm=True)
        print("✓ Skeletons created")
        
        # Implement each test
        print("\n💻 Implementing tests...")
        
        implemented = 0
        failed = 0
        
        while True:
            tests = self.api.next_tests(limit=1)
            
            if not tests:
                break
            
            test = tests[0]
            print(f"\n  [{implemented + 1}] {test['feature_id']}/{test['scenario_id']}")
            
            # Generate implementation
            impl = generate_test_implementation(test)
            
            # Write
            Path(test["test_file"]).write_text(impl)
            
            # Verify
            result = subprocess.run(
                ["pytest", test["test_file"], "-v"],
                capture_output=True
            )
            
            if result.returncode == 0:
                print(f"    ✓ Passed")
                implemented += 1
            else:
                print(f"    ❌ Failed")
                failed += 1
        
        print(f"\n✅ Implementation complete:")
        print(f"   Implemented: {implemented}")
        print(f"   Failed: {failed}")
        
        # Show final coverage
        coverage = self.api.coverage()
        print(f"   Coverage: {coverage['coverage']['overall']['percent']}%")
    
    def run(self, project_dir: Path, prd_file: Optional[Path] = None):
        """Complete workflow."""
        
        print("🚀 SpecLeft Agent Starting...")
        print(f"   Project: {project_dir}")
        
        # Setup
        if not self.setup_project(project_dir):
            return False
        
        # Create specs
        if prd_file:
            if not self.create_specs_from_requirements(prd_file):
                return False
        
        # Generate and implement
        self.generate_and_implement_tests()
        
        print("\n✅ SpecLeft adoption complete!")
        
        return True

# Usage
if __name__ == "__main__":
    agent = SpecLeftAgent()
    agent.run(
        project_dir=Path("."),
        prd_file=Path("docs/PRD.md")
    )
```

---

## Summary

Key points for AI agents using SpecLeft:

1. **Always verify installation** with `specleft doctor --format json`
2. **Check project compatibility** before adopting
3. **Validate specs** before generating tests
4. **Use dry-run** to preview changes
5. **Track progress** with `specleft status` and `specleft next`
6. **Handle errors gracefully** with try/except and retries
7. **Show user progress** throughout the workflow
8. **Use JSON format** for all programmatic access

SpecLeft is designed to be **predictable, safe, and transparent**. Nothing happens without explicit confirmation, and all operations provide clear feedback through JSON outputs.

For more examples and patterns, see the [examples directory](../examples/) in the repository.
