//! Error types for the Archon core library.

use thiserror::Error;

/// Top-level error type for all Archon operations.
#[derive(Debug, Error)]
pub enum ArchonError {
    #[error("Configuration error: {0}")]
    Config(#[from] ConfigError),
    #[error("AI error: {0}")]
    Ai(#[from] AiError),
    #[error("Security error: {0}")]
    Security(#[from] SecurityError),
    #[error("n8n error: {0}")]
    N8n(#[from] N8nError),
    #[error("Distro builder error: {0}")]
    Distro(#[from] DistroError),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

/// Configuration loading and parsing errors.
#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("Config file not found at: {path}")]
    NotFound { path: String },
    #[error("Failed to parse config: {0}")]
    ParseError(String),
    #[error("IO error reading config: {0}")]
    Io(#[from] std::io::Error),
}

/// AI provider and model errors.
#[derive(Debug, Error)]
pub enum AiError {
    #[error("Cannot reach the local Ollama server. Start it with `ollama serve`")]
    OllamaUnavailable,
    #[error("Network error calling AI provider: {0}")]
    NetworkError(String),
    #[error("No models installed. Pull one with `ollama pull qwen3.5:9b`")]
    NoModels,
    #[error("Rate limited by AI provider. Retry after {retry_after_secs}s")]
    RateLimited { retry_after_secs: u64 },
    #[error("AI request timed out after {timeout_secs}s")]
    Timeout { timeout_secs: u64 },
    #[error("Failed to parse AI response: {0}")]
    ParseError(String),
    #[error("Python AI subprocess error: {0}")]
    SubprocessError(String),
}

/// Path and security validation errors.
#[derive(Debug, Error)]
pub enum SecurityError {
    #[error("Path traversal attempt detected in: {path}")]
    PathTraversal { path: String },
    #[error("Permission denied for path: {path}")]
    PermissionDenied { path: String },
    #[error("Shell injection attempt in command: {cmd}")]
    ShellInjection { cmd: String },
    #[error("Null byte detected in input")]
    NullByte,
    #[error("Path outside allowed directories: {path}")]
    PathOutOfBounds { path: String },
}

/// n8n workflow integration errors.
#[derive(Debug, Error)]
pub enum N8nError {
    #[error("n8n connection refused at {url}")]
    ConnectionRefused { url: String },
    #[error("n8n authentication failed — check N8N_API_KEY")]
    AuthFailed,
    #[error("Workflow not found: {id}")]
    WorkflowNotFound { id: String },
    #[error("n8n API error: {0}")]
    ApiError(String),
}

/// Distro builder errors.
#[derive(Debug, Error)]
pub enum DistroError {
    #[error("Root privileges required for distro builds")]
    RootRequired,
    #[error("Required build tool not found: {tool}")]
    MissingTool { tool: String },
    #[error("Build stage '{stage}' failed: {reason}")]
    StageFailed { stage: String, reason: String },
    #[error("Invalid distro profile: {0}")]
    InvalidProfile(String),
}
