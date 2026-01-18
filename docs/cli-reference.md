# SpecLeft CLI Reference

## Features

### `specleft features validate`

Validate Markdown specs.

```bash
specleft features validate [OPTIONS]

Options:
  --dir PATH   Path to features directory (default: features)
```

### `specleft features list`

List features, stories, and scenarios.

```bash
specleft features list [OPTIONS]

Options:
  --dir PATH   Path to features directory (default: features)
```

### `specleft features stats`

Show aggregate statistics for specs.

```bash
specleft features stats [OPTIONS]

Options:
  --dir PATH   Path to features directory (default: features)
```

## Tests

### `specleft test skeleton`

Generate skeleton test files from Markdown specs.

```bash
specleft test skeleton [OPTIONS]

Options:
  -f, --features-dir PATH   Path to features directory (default: features)
  -o, --output-dir PATH     Output directory (default: tests)
  --single-file             Generate all tests in one file
```

### `specleft test report`

Generate an HTML report from test results.

```bash
specleft test report [OPTIONS]

Options:
  -r, --results-file PATH   Specific results JSON file (default: latest)
  -o, --output PATH         Output HTML file (default: report.html)
  --open-browser            Open report in browser after generation
```
