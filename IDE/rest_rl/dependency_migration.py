#!/usr/bin/env python3
"""
Dependency Migration Manager for ReST-RL / GRPO Autonomous Collaborator.

Features:
1. Detects dependency version bumps in Cargo.toml, package.json, pyproject.toml, requirements.txt.
2. Identifies deprecation patterns across multiple source files.
3. Generates unified multi-file changesets for coordinated workspace upgrades.
"""

from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("rest_rl.dependency_migration")


@dataclass
class DependencyBump:
    manifest_file: str
    manifest_type: str  # "cargo", "npm", "pip", "pyproject"
    package_name: str
    old_version: str
    new_version: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FilePatch:
    file_path: str
    original_code: str
    updated_code: str
    diff_hunks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MultiFileChangeset:
    changeset_id: str
    bump: DependencyBump
    patches: List[FilePatch]
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "changeset_id": self.changeset_id,
            "bump": self.bump.to_dict(),
            "patches": [p.to_dict() for p in self.patches],
            "summary": self.summary,
        }


class DependencyMigrationManager:
    """Monitors manifest changes and synthesizes multi-file unified migration changesets."""

    @staticmethod
    def detect_manifest_bumps(
        manifest_filename: str,
        old_content: str,
        new_content: str,
    ) -> List[DependencyBump]:
        """
        Detects version bumps between old and new manifest contents.
        Supports package.json, Cargo.toml, pyproject.toml, and requirements.txt.
        """
        fname = manifest_filename.lower()
        bumps: List[DependencyBump] = []

        if fname.endswith("package.json"):
            bumps.extend(DependencyMigrationManager._detect_npm_bumps(manifest_filename, old_content, new_content))
        elif fname.endswith("cargo.toml"):
            bumps.extend(DependencyMigrationManager._detect_cargo_bumps(manifest_filename, old_content, new_content))
        elif fname.endswith("pyproject.toml"):
            bumps.extend(DependencyMigrationManager._detect_pyproject_bumps(manifest_filename, old_content, new_content))
        elif fname.endswith("requirements.txt"):
            bumps.extend(DependencyMigrationManager._detect_pip_bumps(manifest_filename, old_content, new_content))

        return bumps

    @staticmethod
    def _detect_npm_bumps(filename: str, old_str: str, new_str: str) -> List[DependencyBump]:
        bumps = []
        try:
            old_pkg = json.loads(old_str) if old_str.strip() else {}
            new_pkg = json.loads(new_str) if new_str.strip() else {}

            for section in ("dependencies", "devDependencies"):
                old_deps = old_pkg.get(section, {})
                new_deps = new_pkg.get(section, {})

                for pkg, new_ver in new_deps.items():
                    old_ver = old_deps.get(pkg)
                    if old_ver and old_ver != new_ver:
                        bumps.append(
                            DependencyBump(
                                manifest_file=filename,
                                manifest_type="npm",
                                package_name=pkg,
                                old_version=str(old_ver),
                                new_version=str(new_ver),
                            )
                        )
        except Exception as e:
            logger.debug("Failed parsing package.json: %s", e)
        return bumps

    @staticmethod
    def _detect_cargo_bumps(filename: str, old_str: str, new_str: str) -> List[DependencyBump]:
        bumps = []
        old_deps = DependencyMigrationManager._parse_toml_simple_deps(old_str)
        new_deps = DependencyMigrationManager._parse_toml_simple_deps(new_str)

        for pkg, new_ver in new_deps.items():
            old_ver = old_deps.get(pkg)
            if old_ver and old_ver != new_ver:
                bumps.append(
                    DependencyBump(
                        manifest_file=filename,
                        manifest_type="cargo",
                        package_name=pkg,
                        old_version=old_ver,
                        new_version=new_ver,
                    )
                )
        return bumps

    @staticmethod
    def _detect_pyproject_bumps(filename: str, old_str: str, new_str: str) -> List[DependencyBump]:
        return DependencyMigrationManager._detect_cargo_bumps(filename, old_str, new_str)

    @staticmethod
    def _detect_pip_bumps(filename: str, old_str: str, new_str: str) -> List[DependencyBump]:
        bumps = []
        old_reqs = {}
        for line in old_str.splitlines():
            m = re.match(r"^([a-zA-Z0-9_\-]+)\s*(?:==|>=|~=)\s*([0-9a-zA-Z\.\-]+)", line.strip())
            if m:
                old_reqs[m.group(1).lower()] = m.group(2)

        for line in new_str.splitlines():
            m = re.match(r"^([a-zA-Z0-9_\-]+)\s*(?:==|>=|~=)\s*([0-9a-zA-Z\.\-]+)", line.strip())
            if m:
                pkg = m.group(1).lower()
                new_ver = m.group(2)
                old_ver = old_reqs.get(pkg)
                if old_ver and old_ver != new_ver:
                    bumps.append(
                        DependencyBump(
                            manifest_file=filename,
                            manifest_type="pip",
                            package_name=pkg,
                            old_version=old_ver,
                            new_version=new_ver,
                        )
                    )
        return bumps

    @staticmethod
    def _parse_toml_simple_deps(toml_text: str) -> Dict[str, str]:
        """Simple regex extraction of [dependencies] from TOML."""
        deps = {}
        in_deps = False
        for line in toml_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("["):
                in_deps = "[dependencies" in stripped or "[dev-dependencies" in stripped
                continue

            if in_deps and "=" in stripped and not stripped.startswith("#"):
                parts = stripped.split("=", 1)
                pkg = parts[0].strip().strip('"').strip("'")
                val = parts[1].strip().strip('"').strip("'")
                if "version" in val:
                    m = re.search(r'version\s*=\s*["\'](.*?)["\']', val)
                    if m:
                        val = m.group(1)
                deps[pkg] = val
        return deps

    def create_changeset(
        self,
        changeset_id: str,
        bump: DependencyBump,
        file_replacements: Dict[str, Tuple[str, str]],
    ) -> MultiFileChangeset:
        """
        Builds a MultiFileChangeset given a bump and a dictionary of:
        file_path -> (original_content, migrated_content)
        """
        import difflib

        patches: List[FilePatch] = []
        for fpath, (orig_code, new_code) in file_replacements.items():
            diff = list(
                difflib.unified_diff(
                    orig_code.splitlines(keepends=True),
                    new_code.splitlines(keepends=True),
                    fromfile=fpath,
                    tofile=fpath,
                )
            )
            patches.append(
                FilePatch(
                    file_path=fpath,
                    original_code=orig_code,
                    updated_code=new_code,
                    diff_hunks=["".join(diff)],
                )
            )

        summary = (
            f"Multi-file migration for {bump.package_name} ({bump.old_version} -> {bump.new_version}) "
            f"updating {len(patches)} file(s)."
        )

        return MultiFileChangeset(
            changeset_id=changeset_id,
            bump=bump,
            patches=patches,
            summary=summary,
        )
