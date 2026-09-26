"""Tests for the path validator — safe paths and traversal prevention.

The module under test: archon.security.path_validator

Public surface exercised here:

    PathValidator(allowed_roots, safe_mode=False)
        .validate(path, must_exist=False) -> Path
            must_exist=True  → path must already exist on disk.
        .is_safe(path) -> bool
        .add_allowed_root(root) -> None

    PathValidationError(PermissionError)
        Raised on traversal sequences, blocked system paths, or paths
        outside all configured allowed roots.

    get_path_validator() -> PathValidator
        Module-level singleton.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from archon.security.path_validator import (
    PathValidationError,
    PathValidator,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory as the sole allowed root."""
    return tmp_path


@pytest.fixture
def validator(temp_dir: Path) -> PathValidator:
    return PathValidator(allowed_roots=[temp_dir])


# ─── Safe paths ───────────────────────────────────────────────────────────────


class TestSafePaths:
    def test_path_within_allowed_root_is_valid(
        self, validator: PathValidator, temp_dir: Path
    ) -> None:
        safe_path = temp_dir / "subdir" / "file.txt"
        result = validator.validate(str(safe_path))
        assert result is not None
        assert isinstance(result, Path)

    def test_allowed_root_itself_is_valid(self, validator: PathValidator, temp_dir: Path) -> None:
        result = validator.validate(str(temp_dir))
        assert result is not None
        assert isinstance(result, Path)

    def test_deep_nested_path_within_root_is_valid(
        self, validator: PathValidator, temp_dir: Path
    ) -> None:
        deep = temp_dir / "a" / "b" / "c" / "d.txt"
        result = validator.validate(str(deep))
        assert result is not None

    def test_validate_returns_pathlib_path(self, validator: PathValidator, temp_dir: Path) -> None:
        result = validator.validate(str(temp_dir / "file.txt"))
        assert isinstance(result, Path)

    def test_validate_returns_absolute_path(self, validator: PathValidator, temp_dir: Path) -> None:
        result = validator.validate(str(temp_dir / "file.txt"))
        assert result.is_absolute()

    def test_is_safe_returns_true_for_valid_path(
        self, validator: PathValidator, temp_dir: Path
    ) -> None:
        assert validator.is_safe(temp_dir / "file.txt") is True

    def test_is_safe_returns_true_for_root_itself(
        self, validator: PathValidator, temp_dir: Path
    ) -> None:
        assert validator.is_safe(temp_dir) is True


# ─── Traversal prevention ─────────────────────────────────────────────────────


class TestTraversalPrevention:
    def test_dotdot_sequence_raises(self, validator: PathValidator, temp_dir: Path) -> None:
        """A raw '..' in the path string must be rejected immediately."""
        traversal = str(temp_dir) + "/../../etc/passwd"
        with pytest.raises(PathValidationError):
            validator.validate(traversal)

    def test_absolute_path_inside_blocked_system_prefix_raises(
        self, validator: PathValidator
    ) -> None:
        """/etc is in _BLOCKED_PREFIXES and must be rejected."""
        with pytest.raises(PathValidationError):
            validator.validate("/etc/shadow")

    def test_absolute_path_outside_root_raises(self, validator: PathValidator) -> None:
        """/root/.bashrc is outside the temp_dir allowed root."""
        with pytest.raises(PathValidationError):
            validator.validate("/root/.bashrc")

    def test_is_safe_returns_false_for_traversal(
        self, validator: PathValidator, temp_dir: Path
    ) -> None:
        traversal = str(temp_dir) + "/../../etc/passwd"
        assert validator.is_safe(traversal) is False

    def test_is_safe_returns_false_for_system_path(self, validator: PathValidator) -> None:
        assert validator.is_safe("/etc/passwd") is False

    def test_double_dot_component_raises(self, validator: PathValidator, temp_dir: Path) -> None:
        """A pathlib path constructed with '..' components must be rejected."""
        evil = str(temp_dir / ".." / ".." / "etc" / "passwd")
        with pytest.raises(PathValidationError):
            validator.validate(evil)

    def test_null_byte_in_path_raises(self, validator: PathValidator, temp_dir: Path) -> None:
        """Null bytes in paths are a known injection vector."""
        poisoned = str(temp_dir / "safe_name\x00/etc/passwd")
        with pytest.raises(PathValidationError):
            validator.validate(poisoned)

    def test_path_validation_error_is_permission_error(self, validator: PathValidator) -> None:
        """PathValidationError must be a subclass of PermissionError so it
        propagates correctly through code that only catches PermissionError."""
        with pytest.raises(PermissionError):
            validator.validate("/etc/shadow")


# ─── must_exist=True (must exist) ─────────────────────────────────────────


class TestMustExist:
    def test_allow_create_false_raises_for_nonexistent(
        self, validator: PathValidator, temp_dir: Path
    ) -> None:
        nonexistent = temp_dir / "does_not_exist.txt"
        with pytest.raises(PathValidationError):
            validator.validate(str(nonexistent), must_exist=True)

    def test_allow_create_false_passes_for_existing(
        self, validator: PathValidator, temp_dir: Path
    ) -> None:
        existing = temp_dir / "real_file.txt"
        existing.write_text("hello")
        result = validator.validate(str(existing), must_exist=True)
        assert result.exists()

    def test_allow_create_true_does_not_require_existence(
        self, validator: PathValidator, temp_dir: Path
    ) -> None:
        """Default must_exist=False must not raise for non-existent paths
        within the allowed root."""
        nonexistent = temp_dir / "will_be_created_later.txt"
        result = validator.validate(str(nonexistent), must_exist=False)
        assert result is not None


# ─── add_allowed_root ─────────────────────────────────────────────────────────


class TestAddAllowedRoot:
    def test_newly_added_root_is_accepted(self, tmp_path: Path) -> None:
        extra_root = tmp_path / "extra"
        extra_root.mkdir()

        validator = PathValidator(allowed_roots=[tmp_path / "primary"])
        assert not validator.is_safe(str(extra_root / "file.txt"))

        validator.add_allowed_root(extra_root)
        assert validator.is_safe(str(extra_root / "file.txt"))

    def test_duplicate_root_not_added_twice(self, tmp_path: Path) -> None:
        validator = PathValidator(allowed_roots=[tmp_path])
        initial_count = len(validator._allowed)
        validator.add_allowed_root(tmp_path)
        assert len(validator._allowed) == initial_count


# ─── Default allowed roots ────────────────────────────────────────────────────


class TestDefaultAllowedRoots:
    def test_no_allowed_roots_uses_home_and_tmp(self) -> None:
        """PathValidator() with no arguments should not reject paths under
        the user's home directory or /tmp."""
        validator = PathValidator()
        # /tmp is a default allowed root
        result = validator.validate("/tmp/some_test_file.txt")
        assert result is not None

    def test_path_under_home_directory_is_accepted(self) -> None:
        validator = PathValidator()
        home_path = Path.home() / ".config" / "omni_test_dummy.txt"
        result = validator.validate(str(home_path))
        assert isinstance(result, Path)
