//! Live system telemetry, read directly in Rust via `sysinfo`.
//!
//! Telemetry (CPU / memory / disk / network / processes) is polled frequently
//! by the command center, so it must not pay the cost of spawning Python each
//! time. A persistent `System`/`Networks` pair lives behind a mutex in
//! [`SysState`] so CPU and network-rate deltas are meaningful across polls.
//! Archon's brain (AI, capabilities, workflows, distro) stays in Python; only
//! read-only host telemetry is served here.

use std::sync::Mutex;
use serde::Serialize;
use sysinfo::{Disks, Networks, ProcessesToUpdate, System};
use tauri::State;

/// Persistent telemetry handles. Kept warm so successive polls yield real
/// CPU-usage and network-throughput deltas rather than cold zeros.
pub struct SysState {
    pub sys: Mutex<System>,
    pub networks: Mutex<Networks>,
}

impl SysState {
    pub fn new() -> Self {
        let mut sys = System::new_all();
        sys.refresh_all();
        SysState {
            sys: Mutex::new(sys),
            networks: Mutex::new(Networks::new_with_refreshed_list()),
        }
    }
}

impl Default for SysState {
    fn default() -> Self {
        Self::new()
    }
}

// ── System overview ─────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct DiskInfo {
    pub name: String,
    pub mount: String,
    pub total: u64,
    pub available: u64,
}

#[derive(Serialize)]
pub struct SystemInfo {
    pub host: String,
    pub os: String,
    pub kernel: String,
    pub arch: String,
    pub cpu_model: String,
    pub cpu_cores: usize,
    pub cpu_threads: usize,
    pub cpu_usage: f32,
    pub mem_total: u64,
    pub mem_used: u64,
    pub uptime_secs: u64,
    pub disks: Vec<DiskInfo>,
}

#[tauri::command]
pub fn system_info(state: State<'_, SysState>) -> Result<SystemInfo, String> {
    let mut sys = state.sys.lock().map_err(|e| e.to_string())?;
    sys.refresh_cpu_usage();
    sys.refresh_memory();

    let cpu_model = sys
        .cpus()
        .first()
        .map(|c| c.brand().trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "unknown".into());
    let cpu_threads = sys.cpus().len();
    let cpu_cores = sys.physical_core_count().unwrap_or(cpu_threads);

    let disks = Disks::new_with_refreshed_list()
        .iter()
        .map(|d| DiskInfo {
            name: d.name().to_string_lossy().to_string(),
            mount: d.mount_point().to_string_lossy().to_string(),
            total: d.total_space(),
            available: d.available_space(),
        })
        .collect();

    Ok(SystemInfo {
        host: System::host_name().unwrap_or_else(|| "unknown".into()),
        os: System::long_os_version().unwrap_or_else(|| "unknown".into()),
        kernel: System::kernel_version().unwrap_or_else(|| "unknown".into()),
        arch: System::cpu_arch().unwrap_or_else(|| "unknown".into()),
        cpu_model,
        cpu_cores,
        cpu_threads,
        cpu_usage: sys.global_cpu_usage(),
        mem_total: sys.total_memory(),
        mem_used: sys.used_memory(),
        uptime_secs: System::uptime(),
        disks,
    })
}

// ── Processes ─────────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct ProcessInfo {
    pub pid: u32,
    pub name: String,
    pub cpu: f32,
    pub mem_percent: f32,
}

#[tauri::command]
pub fn list_processes(state: State<'_, SysState>) -> Result<Vec<ProcessInfo>, String> {
    let mut sys = state.sys.lock().map_err(|e| e.to_string())?;
    sys.refresh_processes(ProcessesToUpdate::All, true);
    let total_mem = sys.total_memory().max(1) as f32;

    let mut procs: Vec<ProcessInfo> = sys
        .processes()
        .iter()
        .map(|(pid, p)| ProcessInfo {
            pid: pid.as_u32(),
            name: p.name().to_string_lossy().to_string(),
            cpu: p.cpu_usage(),
            mem_percent: (p.memory() as f32 / total_mem) * 100.0,
        })
        .collect();

    // Newest sort happens client-side; cap here to keep the payload small.
    procs.sort_by(|a, b| b.cpu.partial_cmp(&a.cpu).unwrap_or(std::cmp::Ordering::Equal));
    procs.truncate(80);
    Ok(procs)
}

// ── Network ───────────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct InterfaceInfo {
    pub name: String,
    pub total_received: u64,
    pub total_transmitted: u64,
    pub rx_rate: u64,
    pub tx_rate: u64,
}

#[tauri::command]
pub fn network_info(state: State<'_, SysState>) -> Result<Vec<InterfaceInfo>, String> {
    let mut networks = state.networks.lock().map_err(|e| e.to_string())?;
    networks.refresh();
    let mut out: Vec<InterfaceInfo> = networks
        .iter()
        .map(|(name, data)| InterfaceInfo {
            name: name.clone(),
            total_received: data.total_received(),
            total_transmitted: data.total_transmitted(),
            rx_rate: data.received(),
            tx_rate: data.transmitted(),
        })
        .collect();
    out.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(out)
}

// ── Filesystem (read-only) ────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct DirEntryInfo {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub size: u64,
}

#[derive(Serialize)]
pub struct DirListing {
    pub path: String,
    pub parent: Option<String>,
    pub entries: Vec<DirEntryInfo>,
}

/// Read-only directory listing. Defaults to the user's home when `path` is
/// empty. Never writes; purely reflects what is on disk.
#[tauri::command]
pub fn list_dir(path: Option<String>) -> Result<DirListing, String> {
    let dir = match path {
        Some(p) if !p.is_empty() => std::path::PathBuf::from(p),
        _ => dirs_home(),
    };
    let canonical = dir.canonicalize().unwrap_or(dir);

    let mut entries: Vec<DirEntryInfo> = std::fs::read_dir(&canonical)
        .map_err(|e| format!("{}: {e}", canonical.display()))?
        .filter_map(|e| e.ok())
        .map(|e| {
            let meta = e.metadata().ok();
            let is_dir = meta.as_ref().map(|m| m.is_dir()).unwrap_or(false);
            DirEntryInfo {
                name: e.file_name().to_string_lossy().to_string(),
                path: e.path().to_string_lossy().to_string(),
                is_dir,
                size: meta.map(|m| m.len()).unwrap_or(0),
            }
        })
        .collect();

    // Directories first, then alphabetical.
    entries.sort_by(|a, b| match (a.is_dir, b.is_dir) {
        (true, false) => std::cmp::Ordering::Less,
        (false, true) => std::cmp::Ordering::Greater,
        _ => a.name.to_lowercase().cmp(&b.name.to_lowercase()),
    });

    Ok(DirListing {
        path: canonical.to_string_lossy().to_string(),
        parent: canonical.parent().map(|p| p.to_string_lossy().to_string()),
        entries,
    })
}

fn dirs_home() -> std::path::PathBuf {
    std::env::var_os("HOME")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| std::path::PathBuf::from("/"))
}
