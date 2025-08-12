## [0.3.0] - 2023-10-01
### Added
- CLI command `mtcli coldkey info` to view coldkey information.
- Support Python 3.11 (test fully passed).

### Changed
- Upgrade dependency `cryptography` to 43.0.0.
- Changed struct in `hotkey_manager.py`, separating `import_hotkey` into 2 functions.

### Fixed
- Fix `_hrp` parse error when network=None (#45).
- Fix logger error (does not display "User canceled overwrite").

## [0.2.1] - 2023-09-15
### Fixed
- Patch hotfix: `mnemonic.enc` does not record encoding correctly (#37).