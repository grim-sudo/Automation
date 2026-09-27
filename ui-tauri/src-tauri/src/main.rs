// Prevents additional console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod python;
mod system;

use commands::AppState;
use system::SysState;
use archon_core::config::Config;

fn main() {
    let config = Config::load().unwrap_or_default();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .manage(AppState { config })
        .manage(SysState::new())
        .invoke_handler(tauri::generate_handler![
            commands::send_message,
            commands::execute_command,
            commands::n8n_list_workflows,
            commands::n8n_trigger_workflow,
            commands::n8n_create_workflow,
            commands::distro_list_profiles,
            commands::distro_build,
            commands::get_history,
            commands::get_settings,
            commands::save_settings,
            commands::get_free_models,
            commands::describe_capabilities,
            commands::ai_status,
            system::system_info,
            system::list_processes,
            system::network_info,
            system::list_dir,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
