# SpecLeft for AI Agents

This guide is optimized for AI agents (like Claude Code, Copilot Workspace, Aider, etc.) 
that want to adopt SpecLeft for test specification and generation.

## Quick Evaluation Checklist

Use SpecLeft if the project:
- ✅ Already uses pytest
- ✅ Has features/behaviors to track
- ✅ Needs visibility into test coverage by feature
- ✅ Wants structured test scaffolding

Skip SpecLeft if:
- ❌ Only writing ad-hoc unit tests
- ❌ Tests don't map to features/stories
- ❌ No need for specification tracking

## Installation & Verification
```bash
# Install
pip install specleft

# Verify installation
specleft doctor --format json
# Expect: {"healthy": true, ...}
```

## Common Agent Workflows

### Workflow 1: Add SpecLeft to Existing Project
```python
import subprocess
import json

# 1. Install
subprocess.run(["pip", "install", "specleft"])

# 2. Verify
result = subprocess.run(
    ["specleft", "doctor", "--format", "json"],
    capture_output=True, text=True
)
health = json.loads(result.stdout)
assert health["healthy"], "SpecLeft not properly installed"

# 3. Analyze existing tests
result = subprocess.run(
    ["specleft", "features", "stats"],
    capture_output=True, text=True
)
# Parse output to understand current state

# 4. Create feature specs (see Workflow 2)
```

### Workflow 2: Generate Specs from Requirements
```python
# Given: Product requirements document (PRD)
# Task: Create feature specifications

# 1. Parse requirements and extract features
features = extract_features_from_prd(prd_content)

# 2. Create directory structure
from pathlib import Path

for feature in features:
    feature_dir = Path(f"features/{feature.id}")
    feature_dir.mkdir(parents=True, exist_ok=True)
    
    # Write _feature.md
    (feature_dir / "_feature.md").write_text(f"""---
feature_id: {feature.id}
priority: {feature.priority}
tags: {feature.tags}
---

# Feature: {feature.name}

{feature.description}
""")
    
    for story in feature.stories:
        story_dir = feature_dir / story.id
        story_dir.mkdir(exist_ok=True)
        
        # Write _story.md
        (story_dir / "_story.md").write_text(f"""---
story_id: {story.id}
priority: {story.priority}
---

# Story: {story.name}

{story.description}
""")
        
        # Write scenario files
        for scenario in story.scenarios:
            (story_dir / f"{scenario.id}.md").write_text(f"""---
scenario_id: {scenario.id}
priority: {scenario.priority}
---

# Scenario: {scenario.name}

## Steps
{format_steps(scenario.steps)}
""")

# 3. Validate
result = subprocess.run(
    ["specleft", "features", "validate", "--format", "json"],
    capture_output=True, text=True
)
validation = json.loads(result.stdout)

if not validation["valid"]:
    # Fix errors
    for error in validation["errors"]:
        fix_spec_error(error)
```

### Workflow 3: Generate and Implement Tests
```python
# 1. Generate skeleton tests
subprocess.run(["specleft", "test", "skeleton"])

# 2. Get next test to implement
result = subprocess.run(
    ["specleft", "next", "--limit", "1", "--format", "json"],
    capture_output=True, text=True
)
next_test = json.loads(result.stdout)["tests"][0]

# 3. Read spec file to understand requirements
spec_content = Path(next_test["spec_file"]).read_text()

# 4. Implement test
test_code = generate_test_implementation(
    spec_content=spec_content,
    test_file=next_test["test_file"],
    scenario_id=next_test["scenario_id"]
)

# Write implementation (removes skip=True)
Path(next_test["test_file"]).write_text(test_code)

# 5. Run test to verify
subprocess.run(["pytest", next_test["test_file"]])

# 6. Check coverage progress
result = subprocess.run(
    ["specleft", "status", "--format", "json"],
    capture_output=True, text=True
)
status = json.loads(result.stdout)
print(f"Coverage: {status['summary']['coverage_percent']}%")
```

### Workflow 4: Iterative Test Implementation
```python
# Implement all unimplemented tests
while True:
    # Get next test
    result = subprocess.run(
        ["specleft", "next", "--limit", "1", "--format", "json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    
    if not data["tests"]:
        break  # No more tests to implement
    
    next_test = data["tests"][0]
    
    # Implement
    implement_test(next_test)
    
    # Verify
    test_result = subprocess.run(
        ["pytest", next_test["test_file"]],
        capture_output=True
    )
    
    if test_result.returncode != 0:
        # Test failed, debug and retry
        debug_test_failure(next_test, test_result.stderr)
        continue
    
    # Success, move to next
    print(f"✓ Implemented {next_test['scenario_id']}")

# Final coverage check
result = subprocess.run(
    ["specleft", "status", "--format", "json"],
    capture_output=True, text=True
)
print(json.loads(result.stdout)["summary"])
```

## Programmatic API

All SpecLeft commands support `--format json` for programmatic access:
```python
def get_implementation_status():
    """Get current implementation status."""
    result = subprocess.run(
        ["specleft", "status", "--format", "json"],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)

def get_unimplemented_tests():
    """Get list of tests that need implementation."""
    result = subprocess.run(
        ["specleft", "status", "--unimplemented", "--format", "json"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return [
        scenario
        for feature in data["features"]
        for story in feature["stories"]
        for scenario in story["scenarios"]
        if scenario["status"] == "skipped"
    ]

def validate_specs():
    """Validate all specification files."""
    result = subprocess.run(
        ["specleft", "features", "validate", "--format", "json"],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)
```

## Common Patterns

### Pattern: Check if SpecLeft is appropriate
```python
def should_use_specleft(project_dir: Path) -> bool:
    """Determine if SpecLeft makes sense for this project."""
    
    # Check if pytest is used
    has_pytest = (
        (project_dir / "pytest.ini").exists() or
        (project_dir / "pyproject.toml").read_text().find("pytest") != -1
    )
    
    if not has_pytest:
        return False
    
    # Check if there are features/stories to track
    # (presence of docs, PRD, user stories, etc.)
    has_requirements = (
        (project_dir / "docs").exists() or
        (project_dir / "requirements").exists() or
        len(list(project_dir.glob("**/PRD*.md"))) > 0
    )
    
    return has_requirements
```

### Pattern: Generate spec from test
```python
def reverse_engineer_spec(test_file: Path):
    """Create spec from existing test (for documentation)."""
    
    # Parse test file, extract:
    # - Test function names
    # - Docstrings
    # - Step calls if using specleft.step()
    
    test_ast = ast.parse(test_file.read_text())
    
    for func in test_ast.body:
        if func.name.startswith("test_"):
            scenario_id = func.name.replace("test_", "").replace("_", "-")
            
            # Extract steps from specleft.step() calls
            steps = extract_steps_from_ast(func)
            
            # Create spec file
            create_spec_file(
                scenario_id=scenario_id,
                steps=steps,
                docstring=ast.get_docstring(func)
            )
```

## Error Handling

Always handle potential errors:
```python
try:
    result = subprocess.run(
        ["specleft", "features", "validate", "--format", "json"],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
except subprocess.CalledProcessError as e:
    # Command failed
    print(f"SpecLeft command failed: {e.stderr}")
except json.JSONDecodeError:
    # Invalid JSON output
    print(f"Could not parse SpecLeft output: {result.stdout}")
```

## Tips for Agents

1. **Always validate before generating**: Run `specleft features validate` before `test skeleton`
2. **Use JSON format**: All commands support `--format json` for parsing
3. **Check health first**: Run `specleft doctor` to verify installation
4. **Implement incrementally**: Use `specleft next` to implement one test at a time
5. **Track progress**: Use `specleft status` to show user progress
6. **Handle skipped tests**: Generated tests are skipped by default until implemented