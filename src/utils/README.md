# Utils Module

Common utilities for the VDEH Bibliographic Analysis Project.

## Overview

This module provides reusable utility functions to reduce code duplication across notebooks and scripts.

## Modules

### `notebook_utils.py`

Standard setup functions for Jupyter notebooks.

**Problem Solved:** Every notebook previously had 15+ lines of identical setup code to find the project root and load configuration. This was duplicated across 10+ notebooks (~150 lines of duplication).

**Solution:** Single function call replaces all setup code.

#### Usage

```python
# Old way (15+ lines):
import sys
from pathlib import Path

current_dir = Path.cwd()
project_root = None

for parent in [current_dir] + list(current_dir.parents):
    if (parent / 'config.yaml').exists():
        project_root = parent
        break

if project_root is None:
    raise FileNotFoundError("config.yaml nicht gefunden!")

src_path = project_root / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from config_loader import load_config
config = load_config(project_root / 'config.yaml')


# New way (3 lines):
from utils.notebook_utils import setup_notebook

project_root, config = setup_notebook()
```

#### Available Functions

##### `setup_notebook()`
Complete notebook initialization. Returns `(project_root, config)`.

```python
project_root, config = setup_notebook()
```

**Options:**
- `marker_file='config.yaml'` - File to search for (default: config.yaml)
- `add_src=True` - Add src/ to Python path (default: True)
- `configure_logs=True` - Setup logging (default: True)
- `log_level=logging.INFO` - Logging level (default: INFO)

##### `find_project_root()`
Find project root by searching parent directories.

```python
from pathlib import Path
from utils.notebook_utils import find_project_root

project_root = find_project_root()
print(f"Found: {project_root}")
```

##### `configure_logging()`
Setup logging for notebooks.

```python
import logging
from utils.notebook_utils import configure_logging

configure_logging(level=logging.DEBUG)
```

##### `display_notebook_info()`
Display environment information (useful for debugging).

```python
from utils.notebook_utils import display_notebook_info

project_root, config = setup_notebook()
display_notebook_info(project_root, config)
```

Output:
```
============================================================
NOTEBOOK ENVIRONMENT INFO
============================================================
Project Root        : /path/to/project
Project Name        : VDEH Data Analysis
Project Version     : 2.0.0
Config Path         : /path/to/project/config.yaml
Python Path (src)   : /path/to/project/src
Pandas Version      : 2.0.3
NumPy Version       : 1.24.3
============================================================
```

## Benefits

1. **Reduced Duplication**: Eliminates ~150 lines of duplicated code across notebooks
2. **Consistency**: All notebooks use the same setup pattern
3. **Maintainability**: Changes to setup logic only need to be made once
4. **Error Handling**: Centralized error messages and validation
5. **Documentation**: Well-documented functions with examples
6. **Testing**: Can be unit tested (unlike inline notebook code)

## Migration Guide

To migrate existing notebooks:

1. **Replace setup cell** with:
   ```python
   from utils.notebook_utils import setup_notebook
   project_root, config = setup_notebook()
   ```

2. **Remove these imports** (now handled by setup_notebook):
   - Manual project root finding loop
   - `sys.path.insert()` calls
   - `from config_loader import load_config`

3. **Update import pattern**:
   ```python
   # Old:
   from parsers.vdeh_parser import parse_bibliography

   # New (same, but src/ is already in path):
   from parsers.vdeh_parser import parse_bibliography
   ```

## Development

### Adding New Utilities

When adding new utility functions:

1. Add to appropriate module (or create new if needed)
2. Write docstring with examples
3. Add to `__all__` export list
4. Update this README
5. Add unit tests (when test framework is available)

### Testing

```bash
# Syntax check
python3 -m py_compile src/utils/notebook_utils.py

# Import test
python3 -c "from utils.notebook_utils import setup_notebook; print('OK')"

# Full test (from project root)
python3 -c "
import sys
sys.path.insert(0, 'src')
from utils.notebook_utils import find_project_root
root = find_project_root()
print(f'Found: {root}')
"
```

## See Also

- [config_loader.py](../config_loader.py) - Configuration management
- [notebooks/template_new.ipynb](../../notebooks/template_new.ipynb) - Example notebook using utils
- [Project Documentation](../../README.md) - Main project README
