//! Tauri command handlers — all AI work is delegated to `python archon.py`
//! via subprocess (no shell=true). The Tauri layer handles IPC and config only.

use crate::python::call_python;
use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tauri::State;
use archon_core::config::Config;

/// Shared app state injected into commands via Tauri's State mechanism.
pub struct AppState {
    pub config: Config,
}

// ── Chat ───────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
}

#[tauri::command]
pub async fn send_message(
    message: String,
    history: Vec<ChatMessage>,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let payload = serde_json::json!({
        "action": "chat",
        "message": message,
        "history": history,
    });
    call_python(&state.config, &payload).map_err(|e| e.to_string())
}

// ── Automate ───────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn execute_command(
    command: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let payload = serde_json::json!({
        "action": "run",
        "command": command,
    });
    call_python(&state.config, &payload).map_err(|e| e.to_string())
}

// ── n8n ────────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct Workflow {
    pub id: String,
    pub name: String,
    pub active: bool,
    pub trigger: Option<String>,
    #[serde(rename = "executionCount")]
    pub execution_count: Option<u64>,
}

#[tauri::command]
pub async fn n8n_list_workflows(
    state: State<'_, AppState>,
) -> Result<Vec<Workflow>, String> {
    let payload = serde_json::json!({ "action": "n8n_list" });
    let raw = call_python(&state.config, &payload).map_err(|e| e.to_string())?;
    serde_json::from_str::<Vec<Workflow>>(&raw).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn n8n_trigger_workflow(
    id: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let payload = serde_json::json!({ "action": "n8n_trigger", "id": id });
    call_python(&state.config, &payload).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn n8n_create_workflow(
    name: String,
    description: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let payload = serde_json::json!({
        "action": "n8n_create",
        "name": name,
        "description": description,
    });
    call_python(&state.config, &payload).map_err(|e| e.to_string())?;
    Ok(())
}

// ── Distro ─────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct DistroProfile {
    pub name: String,
    pub description: String,
    pub base: String,
}

#[tauri::command]
pub async fn distro_list_profiles(
    state: State<'_, AppState>,
) -> Result<Vec<DistroProfile>, String> {
    let payload = serde_json::json!({ "action": "distro_profiles" });
    let raw = call_python(&state.config, &payload).map_err(|e| e.to_string())?;
    serde_json::from_str::<Vec<DistroProfile>>(&raw).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn distro_build(
    profile: String,
    output_dir: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let payload = serde_json::json!({
        "action": "distro_build",
        "profile": profile,
        "output_dir": output_dir,
    });
    call_python(&state.config, &payload).map_err(|e| e.to_string())
}

// ── History ────────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct HistoryEntry {
    pub id: String,
    pub command: String,
    pub status: String,
    pub timestamp: String,
    pub output: Option<String>,
}

#[tauri::command]
pub async fn get_history(
    state: State<'_, AppState>,
) -> Result<Vec<HistoryEntry>, String> {
    let payload = serde_json::json!({ "action": "history" });
    let raw = call_python(&state.config, &payload).map_err(|e| e.to_string())?;
    serde_json::from_str::<Vec<HistoryEntry>>(&raw).map_err(|e| e.to_string())
}

// ── Settings ───────────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize)]
pub struct Settings {
    pub openrouter_api_key: String,
    pub n8n_url: String,
    pub n8n_api_key: String,
    pub debug: bool,
    pub safe_mode: bool,
}

#[tauri::command]
pub async fn get_settings(
    state: State<'_, AppState>,
) -> Result<Settings, String> {
    Ok(Settings {
        openrouter_api_key: state.config.ai.openrouter_api_key.clone(),
        n8n_url:            state.config.n8n.url.clone(),
        n8n_api_key:        state.config.n8n.api_key.clone(),
        debug:              state.config.debug,
        safe_mode:          state.config.safe_mode,
    })
}

#[tauri::command]
pub async fn save_settings(
    settings: Settings,
    _state: State<'_, AppState>,
) -> Result<(), String> {
    // Write to ~/.archon/config.toml using Python to preserve TOML formatting.
    let payload = serde_json::json!({
        "action": "save_settings",
        "settings": settings,
    });
    // Fire-and-forget; ignore errors from Python side.
    let _ = call_python(&_state.config, &payload);
    Ok(())
}

// ── Models ─────────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn get_free_models(
    state: State<'_, AppState>,
) -> Result<Vec<HashMap<String, String>>, String> {
    let payload = serde_json::json!({ "action": "models" });
    let raw = call_python(&state.config, &payload).map_err(|e| e.to_string())?;
    serde_json::from_str(&raw).map_err(|e| e.to_string())
}
