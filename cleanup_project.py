#!/usr/bin/env python3
"""
Project Cleanup Script for ModernTensor Aptos
Safely removes duplicate files, backup files, and test files while preserving important core files.
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
import hashlib


class ProjectCleaner:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "cleanup_backup"
        self.removed_files = []
        self.preserved_files = []

        # Files that should NEVER be deleted (core functionality)
        self.critical_files = {
            "README.md",
            "README_CORE.md",
            "requirements.txt",
            "requirements-ci.txt",
            "requirements-test.txt",
            "pyproject.toml",
            "pytest.ini",
            "setup.py",
            "Dockerfile",
            ".dockerignore",
            "LICENSE",
            "CHANGELOG.md",
            "MIGRATION.md",
            "PRODUCTION_DEPLOYMENT.md",
            "DEPLOYMENT_COMPLETED.md",
            "LEGACY_CLEANUP_SUMMARY.md",
            "__init__.py",
            ".gitignore",
            ".gitmodules",
            "moderntensor.png",
            "mt_core/__init__.py",
            "mt_core/account.py",
            "mt_core/async_client.py",
            "mt_core/core_client/__init__.py",
            "mt_core/consensus/__init__.py",
            "mt_core/formulas/__init__.py",
            "mt_core/keymanager/__init__.py",
            "mt_core/metagraph/__init__.py",
            "mt_core/network/__init__.py",
            "mt_core/node/__init__.py",
            "mt_core/service/__init__.py",
            "mt_core/smartcontract/__init__.py",
            "mt_core/utils/__init__.py",
            "tests/__init__.py",
            "examples/__init__.py",
            "network/__init__.py",
            "config/__init__.py",
            "scripts/__init__.py",
            "docker/__init__.py",
            "docs/__init__.py",
            "subnet1_coreDAO/__init__.py",
            "test_real_wallet/__init__.py",
            ".github/workflows/",
            ".vscode/settings.json",
        }

        # Patterns for files that can be safely removed
        self.removable_patterns = [
            # Duplicate files with numbers
            r".* \d+\.py$",
            r".* \d+\.json$",
            r".* \d+\.md$",
            r".* \d+\.txt$",
            r".* \d+\.move$",
            r".* \d+\.backup.*$",
            r".* \d+\.v\d+$",
            # Backup files
            r".*\.backup.*$",
            r".*\.v\d+$",
            r".*_backup.*$",
            r".*_v\d+$",
            # Test files with numbers
            r"test_.* \d+\.py$",
            r"check_.* \d+\.py$",
            r"register_.* \d+\.move$",
            r"create_.* \d+\.move$",
            r"initialize_.* \d+\.move$",
            r"prepare_.* \d+\.py$",
            # Log files
            r".*\.log$",
            # Temporary files
            r".*\.tmp$",
            r".*\.temp$",
        ]

        # Directories that can be cleaned up
        self.cleanup_dirs = ["backup"]

    def create_backup(self):
        """Create backup of files before deletion"""
        print("Creating backup directory...")
        self.backup_dir.mkdir(exist_ok=True)

        # Create timestamp for backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_log = self.backup_dir / f"cleanup_log_{timestamp}.json"

        return backup_log

    def is_critical_file(self, file_path):
        """Check if file is critical and should not be deleted"""
        rel_path = str(file_path.relative_to(self.project_root))
        return rel_path in self.critical_files

    def should_remove_file(self, file_path):
        """Determine if file should be removed based on patterns"""
        if self.is_critical_file(file_path):
            return False

        filename = file_path.name

        # Check removable patterns
        import re

        for pattern in self.removable_patterns:
            if re.match(pattern, filename):
                return True

        return False

    def get_file_hash(self, file_path):
        """Get MD5 hash of file content"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None

    def find_duplicates(self):
        """Find duplicate files based on content hash"""
        hash_map = {}
        duplicates = []

        for file_path in self.project_root.rglob("*"):
            if file_path.is_file() and not self.is_critical_file(file_path):
                file_hash = self.get_file_hash(file_path)
                if file_hash:
                    if file_hash in hash_map:
                        duplicates.append((file_path, hash_map[file_hash]))
                    else:
                        hash_map[file_hash] = file_path

        return duplicates

    def backup_file(self, file_path):
        """Backup file before deletion"""
        if file_path.is_file():
            rel_path = file_path.relative_to(self.project_root)
            backup_path = self.backup_dir / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, backup_path)
            return str(backup_path)
        return None

    def cleanup_files(self):
        """Main cleanup process"""
        print("Starting project cleanup...")

        # Create backup
        backup_log = self.create_backup()

        # Find and remove duplicate files
        duplicates = self.find_duplicates()
        print(f"Found {len(duplicates)} duplicate files")

        for duplicate, original in duplicates:
            if self.should_remove_file(duplicate):
                backup_path = self.backup_file(duplicate)
                try:
                    duplicate.unlink()
                    self.removed_files.append(
                        {
                            "file": str(duplicate),
                            "backup": backup_path,
                            "reason": "duplicate",
                            "original": str(original),
                        }
                    )
                    print(f"Removed duplicate: {duplicate}")
                except Exception as e:
                    print(f"Error removing {duplicate}: {e}")

        # Remove files matching removable patterns
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file() and self.should_remove_file(file_path):
                backup_path = self.backup_file(file_path)
                try:
                    file_path.unlink()
                    self.removed_files.append(
                        {
                            "file": str(file_path),
                            "backup": backup_path,
                            "reason": "pattern_match",
                        }
                    )
                    print(f"Removed: {file_path}")
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")

        # Clean up specific directories
        for dir_name in self.cleanup_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                backup_path = self.backup_file(dir_path)
                try:
                    shutil.rmtree(dir_path)
                    self.removed_files.append(
                        {
                            "file": str(dir_path),
                            "backup": backup_path,
                            "reason": "cleanup_directory",
                        }
                    )
                    print(f"Removed directory: {dir_path}")
                except Exception as e:
                    print(f"Error removing directory {dir_path}: {e}")

        # Save cleanup log
        cleanup_summary = {
            "timestamp": datetime.now().isoformat(),
            "removed_files": self.removed_files,
            "total_removed": len(self.removed_files),
            "backup_location": str(self.backup_dir),
        }

        with open(backup_log, "w") as f:
            json.dump(cleanup_summary, f, indent=2)

        # Save summary in project root
        summary_file = self.project_root / "cleanup_summary.json"
        with open(summary_file, "w") as f:
            json.dump(cleanup_summary, f, indent=2)

        print(f"\nCleanup completed!")
        print(f"Total files removed: {len(self.removed_files)}")
        print(f"Backup location: {self.backup_dir}")
        print(f"Summary saved to: {summary_file}")

    def dry_run(self):
        """Show what would be cleaned without actually doing it"""
        print("DRY RUN - No files will be actually removed")
        print("=" * 50)

        potential_removals = []

        # Check for duplicates
        duplicates = self.find_duplicates()
        for duplicate, original in duplicates:
            if self.should_remove_file(duplicate):
                potential_removals.append(
                    {
                        "file": str(duplicate),
                        "reason": f"duplicate of {original}",
                        "type": "duplicate",
                    }
                )

        # Check for pattern matches
        for file_path in self.project_root.rglob("*"):
            if file_path.is_file() and self.should_remove_file(file_path):
                potential_removals.append(
                    {
                        "file": str(file_path),
                        "reason": "matches removal pattern",
                        "type": "pattern",
                    }
                )

        # Check cleanup directories
        for dir_name in self.cleanup_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                potential_removals.append(
                    {
                        "file": str(dir_path),
                        "reason": "cleanup directory",
                        "type": "directory",
                    }
                )

        print(
            f"Found {len(potential_removals)} files/directories that could be removed:"
        )
        print()

        for item in potential_removals:
            print(f"[{item['type'].upper()}] {item['file']}")
            print(f"  Reason: {item['reason']}")
            print()

        print(f"Total: {len(potential_removals)} items")
        print("\nRun without --dry-run to actually perform cleanup")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Clean up ModernTensor Aptos project")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without actually doing it",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args()

    cleaner = ProjectCleaner(args.project_root)

    if args.dry_run:
        cleaner.dry_run()
    else:
        # Ask for confirmation
        print("This will remove duplicate files, backup files, and test files.")
        print("A backup will be created before any deletion.")
        response = input("Continue? (y/N): ")

        if response.lower() in ["y", "yes"]:
            cleaner.cleanup_files()
        else:
            print("Cleanup cancelled.")


if __name__ == "__main__":
    main()
