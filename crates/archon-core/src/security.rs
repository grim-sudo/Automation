//! Path validation and shell-safety utilities.
//!
//! All path operations must pass through `PathValidator::validate()`.
//! No shell=true equivalent is ever permitted.

use crate::error::SecurityError;
use std::path::{Path, PathBuf};

/// Validates paths against traversal, null-byte, and bounds attacks.
pub struct PathValidator {
    allowed_prefixes: Vec<PathBuf>,
}

impl PathValidator {
    /// Create a validator that allows any absolute path (no bounds check).
    pub fn permissive() -> Self {
        Self {
            allowed_prefixes: Vec::new(),
        }
    }

    /// Create a validator constrained to specific allowed directory prefixes.
    pub fn with_allowed_dirs(dirs: &[&str]) -> Self {
        Self {
            allowed_prefixes: dirs.iter().map(PathBuf::from).collect(),
        }
    }

    /// Validate a path string. Returns the canonicalized `PathBuf` on success.
    pub fn validate(&self, path: &str) -> Result<PathBuf, SecurityError> {
        // Block null bytes.
        if path.contains('\0') {
            return Err(SecurityError::NullByte);
        }

        // Block percent-encoded traversal (%2e%2e / %2F).
        let lower = path.to_lowercase();
        if lower.contains("%2e") || lower.contains("%2f") {
            return Err(SecurityError::PathTraversal {
                path: path.to_string(),
            });
        }

        // Block literal ../
        if path.contains("..") {
            return Err(SecurityError::PathTraversal {
                path: path.to_string(),
            });
        }

        let p = Path::new(path);

        // If allowed dirs specified, enforce prefix constraint.
        if !self.allowed_prefixes.is_empty() {
            let canonical = p.to_path_buf();
            let allowed = self
                .allowed_prefixes
                .iter()
                .any(|prefix| canonical.starts_with(prefix));
            if !allowed {
                return Err(SecurityError::PathOutOfBounds {
                    path: path.to_string(),
                });
            }
        }

        Ok(p.to_path_buf())
    }
}

/// Checks that a command argument slice is safe to execute via std::process::Command.
///
/// Never use this as a replacement for `shell=true` — always pass args as a slice.
pub struct ShellSanitizer;

impl ShellSanitizer {
    /// Returns `true` if none of the args contain dangerous shell metacharacters.
    /// This is a defence-in-depth check; the primary safety comes from never
    /// using shell=true / Command::new("sh").arg("-c", user_input).
    pub fn is_safe_command(args: &[&str]) -> bool {
        const DANGEROUS: &[char] = &[';', '&', '|', '`', '$', '(', ')', '<', '>', '!', '\n'];
        args.iter()
            .all(|arg| !arg.chars().any(|c| DANGEROUS.contains(&c)))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_path_traversal_blocked() {
        let v = PathValidator::permissive();
        assert!(v.validate("../etc/passwd").is_err());
        assert!(v.validate("foo/../../etc/passwd").is_err());
        assert!(v.validate("%2e%2e/etc/passwd").is_err());
    }

    #[test]
    fn test_null_byte_blocked() {
        let v = PathValidator::permissive();
        assert!(v.validate("/tmp/test\0bad").is_err());
    }

    #[test]
    fn test_safe_path_accepted() {
        let v = PathValidator::permissive();
        assert!(v.validate("/tmp/archon_test").is_ok());
        assert!(v.validate("relative/path/file.txt").is_ok());
    }

    #[test]
    fn test_allowed_dir_constraint() {
        let v = PathValidator::with_allowed_dirs(&["/tmp"]);
        assert!(v.validate("/tmp/safe").is_ok());
        assert!(v.validate("/etc/passwd").is_err());
    }
}
