//! Python subprocess bridge.
//!
//! Spawns `python tyranos.py --tauri-ipc` and sends a JSON payload on stdin.
//! Reads JSON from stdout as the response. No `shell=true` equivalent is used.

use anyhow::{bail, Context, Result};
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use tyranos_core::config::Config;

/// Detect the best Python interpreter to use.
fn find_python(project_root: &std::path::Path) -> PathBuf {
    let venv = project_root.join(".venv").join("bin").join("python");
    if venv.exists() {
        return venv;
    }
    // Fall back to system python3 / python.
    for name in &["python3", "python"] {
        if let Some(p) = which_python(name) {
            return p;
        }
    }
    PathBuf::from("python3")
}

fn which_python(name: &str) -> Option<PathBuf> {
    std::process::Command::new("which")
        .arg(name)
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                let s = String::from_utf8_lossy(&o.stdout).trim().to_string();
                if s.is_empty() { None } else { Some(PathBuf::from(s)) }
            } else {
                None
            }
        })
}

/// Call Python with a JSON payload; return the stdout string.
pub fn call_python(config: &Config, payload: &serde_json::Value) -> Result<String> {
    let project_root = project_root();
    let python = find_python(&project_root);
    let tyranos_py = project_root.join("tyranos.py");

    if !tyranos_py.exists() {
        bail!("tyranos.py not found at {:?}", tyranos_py);
    }

    let json_input = serde_json::to_string(payload)
        .context("Failed to serialise payload to JSON")?;

    let mut child = Command::new(&python)
        .arg(&tyranos_py)
        .arg("--tauri-ipc")
        .env("TYRANOS_GUI", "tauri")
        .env_clear()
        .envs(std::env::vars())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .with_context(|| format!("Failed to spawn {:?}", python))?;

    // Write JSON payload to stdin then close it.
    if let Some(mut stdin) = child.stdin.take() {
        stdin
            .write_all(json_input.as_bytes())
            .context("Failed to write to Python stdin")?;
    }

    let output = child.wait_with_output().context("Python subprocess error")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        bail!("Python exited with {}: {}", output.status, stderr);
    }

    Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

/// Returns the project root (two levels up from the src-tauri/src directory).
fn project_root() -> PathBuf {
    // At runtime the binary is in ui-tauri/src-tauri/target/…
    // We walk up to find tyranos.py.
    let exe = std::env::current_exe().unwrap_or_default();
    let mut dir = exe.parent().unwrap_or(&exe).to_path_buf();
    for _ in 0..6 {
        if dir.join("tyranos.py").exists() {
            return dir;
        }
        if let Some(parent) = dir.parent() {
            dir = parent.to_path_buf();
        } else {
            break;
        }
    }
    std::env::current_dir().unwrap_or_default()
}
