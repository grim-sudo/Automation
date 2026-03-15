//! AI client that delegates to the Python AI layer via subprocess JSON-RPC.
//!
//! As documented in docs/MIGRATION.md Phase 1: for AI operations the Rust CLI
//! spawns `python -m tyranos.ai <json>` and parses the stdout response.
//! This keeps the Python AI layer (httpx, tenacity, tiktoken) untouched.

use crate::error::AiError;
use serde::{Deserialize, Serialize};
use std::process::{Command, Stdio};
use std::time::Duration;

/// A single message in conversation context.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
}

/// A single planned task step from the AI.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub action: String,
    pub description: String,
    #[serde(default)]
    pub params: serde_json::Value,
}

/// Response from the Python AI layer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiResponse {
    pub intent: String,
    pub tasks: Vec<Task>,
    pub confidence: f32,
    pub model_used: String,
    pub tokens: u32,
    #[serde(default)]
    pub error: Option<String>,
}

/// Input sent to the Python AI subprocess.
#[derive(Debug, Serialize)]
struct AiRequest<'a> {
    command: &'a str,
    context: &'a [Message],
    safe_mode: bool,
}

/// Calls the Python AI layer via `python -m tyranos.ai <json>`.
pub struct AiClient {
    timeout: Duration,
    python_executable: String,
}

impl AiClient {
    pub fn new() -> Self {
        Self {
            timeout: Duration::from_secs(30),
            python_executable: Self::detect_python(),
        }
    }

    pub fn with_timeout(mut self, secs: u64) -> Self {
        self.timeout = Duration::from_secs(secs);
        self
    }

    /// Execute an AI request and return the response.
    pub fn execute(
        &self,
        command: &str,
        context: &[Message],
        safe_mode: bool,
    ) -> Result<AiResponse, AiError> {
        let request = AiRequest {
            command,
            context,
            safe_mode,
        };
        let json_input =
            serde_json::to_string(&request).map_err(|e| AiError::SubprocessError(e.to_string()))?;

        let output = Command::new(&self.python_executable)
            .args(["-m", "tyranos.ai"])
            .arg(&json_input)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .output()
            .map_err(|e| AiError::SubprocessError(format!("Failed to spawn python: {e}")))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(AiError::SubprocessError(stderr.into_owned()));
        }

        if output.stdout.is_empty() {
            return Err(AiError::SubprocessError(
                "Python AI returned empty response".to_string(),
            ));
        }

        serde_json::from_slice(&output.stdout)
            .map_err(|e| AiError::ParseError(format!("Failed to parse AI JSON response: {e}")))
    }

    /// Detect the Python executable to use.
    fn detect_python() -> String {
        // Prefer the venv python if we're running from the project directory.
        let venv_python = ".venv/bin/python";
        if std::path::Path::new(venv_python).exists() {
            return venv_python.to_string();
        }
        "python3".to_string()
    }
}

impl Default for AiClient {
    fn default() -> Self {
        Self::new()
    }
}
