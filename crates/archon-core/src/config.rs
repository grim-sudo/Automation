//! Configuration loading for Archon.
//!
//! Priority: env var > ~/.archon/config.toml > built-in default.
//! Mirrors the field structure of archon/config.py.

use crate::error::ConfigError;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Top-level Archon configuration.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Config {
    #[serde(default)]
    pub ai: AiConfig,
    #[serde(default)]
    pub n8n: N8nConfig,
    #[serde(default)]
    pub distro_builder: DistroConfig,
    #[serde(default)]
    pub debug: bool,
    #[serde(default)]
    pub safe_mode: bool,
}

/// AI provider configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AiConfig {
    pub openrouter_api_key: String,
    pub openrouter_base_url: String,
    pub model: String,
    pub max_tokens: u32,
    pub timeout_secs: u64,
    pub max_retries: u32,
}

impl Default for AiConfig {
    fn default() -> Self {
        Self {
            openrouter_api_key: String::new(),
            openrouter_base_url: "https://openrouter.ai/api/v1".to_string(),
            model: String::new(),
            max_tokens: 8000,
            timeout_secs: 30,
            max_retries: 3,
        }
    }
}

/// n8n connection configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct N8nConfig {
    pub url: String,
    pub api_key: String,
}

impl Default for N8nConfig {
    fn default() -> Self {
        Self {
            url: "http://localhost:5678".to_string(),
            api_key: String::new(),
        }
    }
}

/// Distro builder configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DistroConfig {
    pub work_dir: PathBuf,
    pub output_dir: PathBuf,
}

impl Default for DistroConfig {
    fn default() -> Self {
        Self {
            work_dir: PathBuf::from("/tmp/archon_distro_build"),
            output_dir: PathBuf::from("./distro_output"),
        }
    }
}

impl Config {
    /// Load configuration from file and environment variables.
    ///
    /// Priority: env var > config file > built-in default.
    pub fn load() -> Result<Self, ConfigError> {
        let mut cfg = Self::load_file()?;
        cfg.apply_env_overrides();
        Ok(cfg)
    }

    /// Load from ~/.archon/config.toml (returns defaults if file absent).
    fn load_file() -> Result<Self, ConfigError> {
        let config_path = dirs_config_path();
        if !config_path.exists() {
            return Ok(Self::default());
        }
        let content = std::fs::read_to_string(&config_path)?;
        toml::from_str(&content).map_err(|e| ConfigError::ParseError(e.to_string()))
    }

    /// Apply environment variable overrides on top of file config.
    fn apply_env_overrides(&mut self) {
        if let Ok(v) = std::env::var("OPENROUTER_API_KEY") {
            if !v.is_empty() {
                self.ai.openrouter_api_key = v;
            }
        }
        if let Ok(v) = std::env::var("N8N_URL") {
            if !v.is_empty() {
                self.n8n.url = v;
            }
        }
        if let Ok(v) = std::env::var("N8N_API_KEY") {
            if !v.is_empty() {
                self.n8n.api_key = v;
            }
        }
        if std::env::var("ARCHON_DEBUG").is_ok() {
            self.debug = true;
        }
        if std::env::var("ARCHON_SAFE_MODE").is_ok() {
            self.safe_mode = true;
        }
    }
}

/// Returns the path to the Archon config file.
fn dirs_config_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/root".to_string());
    PathBuf::from(home).join(".archon").join("config.toml")
}
