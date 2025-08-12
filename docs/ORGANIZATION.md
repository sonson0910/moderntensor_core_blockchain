# ModernTensor Aptos SDK - Project Organization

## Directory Structure

```
moderntensor_aptos/
├── mt_core/              # Core functionality
├── mt_aptos/             # Aptos-specific implementations
├── tests/                # Test files
├── scripts/              # Utility scripts
├── docs/                 # Documentation
├── config/               # Configuration files
├── docker/               # Docker files
├── assets/               # Images and assets
├── network/              # Network-related code
├── slot_coordination/    # Slot coordination system
├── examples/             # Example code
└── backup/               # Backup of original files
```

## File Organization

### Tests (`tests/`)
- All test files (`test_*.py`, `*_test.py`)
- Test configuration files

### Scripts (`scripts/`)
- Utility scripts (`quick_*.py`, `check_*.py`, etc.)
- Maintenance and deployment scripts

### Documentation (`docs/`)
- Markdown files
- Text documentation

### Configuration (`config/`)
- JSON, YAML, TOML configuration files
- Settings and parameters

### Docker (`docker/`)
- Dockerfile and related files
- Container configuration

### Assets (`assets/`)
- Images, icons, and other static assets

## Import Paths

All import paths have been updated to reflect the new organization.
If you encounter import errors, please check the updated paths.

## Migration Notes

- Critical files like `__init__.py`, `setup.py`, etc. remain in their original locations
- Test files are now in the `tests/` directory
- Utility scripts are organized in the `scripts/` directory
- Documentation is centralized in the `docs/` directory

## Development

When adding new files:
1. Place test files in `tests/`
2. Place utility scripts in `scripts/`
3. Place documentation in `docs/`
4. Place configuration files in `config/`
5. Place assets in `assets/`

This organization makes the project more maintainable and easier to navigate.
