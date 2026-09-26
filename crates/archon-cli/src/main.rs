//! Archon CLI binary — fast Rust alternative to `python archon.py`.
//!
//! Activated via: ARCHON_RUST_CLI=1
//! Delegates AI-heavy operations to the Python layer via subprocess JSON-RPC.
//! See docs/MIGRATION.md Phase 1 for the full design rationale.

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use colored::Colorize;
use std::path::PathBuf;
use archon_core::{config::Config, intent::NlpEngine, security::PathValidator};

// ── CLI argument structure ─────────────────────────────────────────────────────

#[derive(Parser)]
#[command(name = "archon")]
#[command(about = "Universal Automation Intelligence — Rust CLI")]
#[command(version = env!("CARGO_PKG_VERSION"))]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Enable verbose debug output.
    #[arg(long, global = true)]
    debug: bool,

    /// Require confirmation before destructive operations.
    #[arg(long, global = true)]
    safe_mode: bool,

    /// Write structured JSON logs to FILE.
    #[arg(long, global = true, value_name = "FILE")]
    log_file: Option<PathBuf>,
}

#[derive(Subcommand)]
enum Commands {
    /// Execute a natural-language command.
    Run {
        /// The command to execute (e.g. "create folder reports").
        #[arg(value_name = "COMMAND")]
        command: String,

        /// Drop into interactive confirmation mode.
        #[arg(short = 'i', long)]
        interactive: bool,
    },

    /// Launch the GUI (delegates to Python; use ARCHON_GUI=tauri for Tauri).
    Gui,

    /// Execute all commands from a file (one per line).
    Batch {
        /// Path to the commands file.
        file: PathBuf,
    },

    /// n8n workflow management.
    N8n {
        #[command(subcommand)]
        action: N8nCommands,
    },

    /// Custom Linux distro builder.
    Distro {
        #[command(subcommand)]
        action: DistroCommands,
    },

    /// List available free AI models from OpenRouter.
    Models,

    /// Print version information.
    Version,
}

#[derive(Subcommand)]
enum N8nCommands {
    /// List all n8n workflows.
    List,
    /// Create a new workflow from a natural-language description.
    Create { description: String },
    /// Trigger a workflow by ID.
    Run {
        id: String,
        /// Optional JSON payload for webhook triggers.
        #[arg(long)]
        payload: Option<String>,
    },
    /// Show execution status for a workflow.
    Status { id: String },
}

#[derive(Subcommand)]
enum DistroCommands {
    /// Build a custom Linux ISO.
    Build {
        /// Natural-language description of the distro to build.
        #[arg(long)]
        nl: Option<String>,
        /// Path to a TOML distro profile.
        #[arg(long)]
        profile: Option<PathBuf>,
        /// Output directory for the ISO.
        #[arg(long)]
        output: PathBuf,
    },
    /// List available distro profiles.
    Profiles,
    /// Estimate build time and resources for a description.
    Estimate { description: String },
}

// ── Entry point ────────────────────────────────────────────────────────────────

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    let cfg = Config::load().unwrap_or_default();
    let nlp = NlpEngine::new();

    if cli.debug {
        eprintln!("{}", "Debug mode enabled".dimmed());
    }

    match cli.command {
        Commands::Run {
            command,
            interactive,
        } => handle_run(&command, interactive, &cfg, &nlp, cli.safe_mode),
        Commands::Gui => handle_gui(),
        Commands::Batch { file } => handle_batch(&file, &cfg, &nlp, cli.safe_mode),
        Commands::N8n { action } => handle_n8n(action, &cfg),
        Commands::Distro { action } => handle_distro(action, &cfg),
        Commands::Models => handle_models(),
        Commands::Version => handle_version(),
    }
}

// ── Command handlers ──────────────────────────────────────────────────────────

fn handle_run(
    command: &str,
    _interactive: bool,
    cfg: &Config,
    nlp: &NlpEngine,
    safe_mode: bool,
) -> Result<()> {
    let intent = nlp.parse(command);
    println!(
        "{} {} (confidence {:.0}%)",
        "→".cyan().bold(),
        intent.intent.to_string().purple(),
        intent.confidence * 100.0,
    );

    // Delegate to Python for actual execution.
    delegate_to_python(
        &["run", command, if safe_mode { "--safe-mode" } else { "" }],
        cfg,
    )
}

fn handle_gui() -> Result<()> {
    let gui_backend = std::env::var("ARCHON_GUI").unwrap_or_else(|_| "ctk".to_string());
    if gui_backend == "tauri" {
        let binary = find_tauri_binary();
        if let Some(bin) = binary {
            let status = std::process::Command::new(&bin)
                .status()
                .with_context(|| format!("Failed to launch Tauri binary at {bin:?}"))?;
            std::process::exit(status.code().unwrap_or(1));
        }
        eprintln!(
            "{}",
            "⚠  Tauri binary not found — falling back to CustomTkinter".yellow()
        );
    }
    // Fall through to Python CTk GUI.
    delegate_to_python(&["gui"], &Config::default())
}

fn handle_batch(file: &PathBuf, cfg: &Config, nlp: &NlpEngine, safe_mode: bool) -> Result<()> {
    // Validate the file path before reading.
    let validator = PathValidator::permissive();
    validator
        .validate(file.to_str().unwrap_or(""))
        .context("Invalid batch file path")?;

    let content = std::fs::read_to_string(file)
        .with_context(|| format!("Cannot read batch file: {file:?}"))?;

    let mut ok = 0usize;
    let mut fail = 0usize;

    for (line_no, line) in content.lines().enumerate() {
        let line = line.trim();
        // Skip blank lines and comments.
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        println!("{} [{}] {}", "▶".cyan(), line_no + 1, line);
        match handle_run(line, false, cfg, nlp, safe_mode) {
            Ok(_) => {
                println!("{}", "  ✓ OK".green());
                ok += 1;
            }
            Err(e) => {
                eprintln!("{} {e}", "  ✗ Error:".red());
                fail += 1;
            }
        }
    }

    println!("\n{ok} succeeded, {fail} failed");
    if fail > 0 {
        std::process::exit(1);
    }
    Ok(())
}

fn handle_n8n(action: N8nCommands, cfg: &Config) -> Result<()> {
    let args: Vec<String> = match action {
        N8nCommands::List => vec!["n8n".to_string(), "list".to_string()],
        N8nCommands::Create { description } => {
            vec!["n8n".to_string(), "create".to_string(), description]
        }
        N8nCommands::Run { id, payload } => {
            let mut a = vec!["n8n".to_string(), "run".to_string(), id];
            if let Some(p) = payload {
                a.extend(["--payload".to_string(), p]);
            }
            a
        }
        N8nCommands::Status { id } => {
            vec!["n8n".to_string(), "status".to_string(), id]
        }
    };
    let arg_refs: Vec<&str> = args.iter().map(String::as_str).collect();
    delegate_to_python(&arg_refs, cfg)
}

fn handle_distro(action: DistroCommands, cfg: &Config) -> Result<()> {
    let args: Vec<String> = match action {
        DistroCommands::Build {
            nl,
            profile,
            output,
        } => {
            let mut a = vec!["distro".to_string(), "build".to_string()];
            if let Some(d) = nl {
                a.extend(["--nl".to_string(), d]);
            }
            if let Some(p) = profile {
                a.extend(["--profile".to_string(), p.display().to_string()]);
            }
            a.extend(["--output".to_string(), output.display().to_string()]);
            a
        }
        DistroCommands::Profiles => vec!["distro".to_string(), "profiles".to_string()],
        DistroCommands::Estimate { description } => {
            vec!["distro".to_string(), "estimate".to_string(), description]
        }
    };
    let arg_refs: Vec<&str> = args.iter().map(String::as_str).collect();
    delegate_to_python(&arg_refs, cfg)
}

fn handle_models() -> Result<()> {
    delegate_to_python(&["models"], &Config::default())
}

fn handle_version() -> Result<()> {
    println!(
        "Archon {} (Rust CLI, {})",
        env!("CARGO_PKG_VERSION"),
        env!("CARGO_PKG_DESCRIPTION"),
    );
    delegate_to_python(&["--version"], &Config::default())
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Delegate a subcommand to the Python CLI via subprocess.
/// Uses list-form args — never shell=true.
fn delegate_to_python(args: &[&str], _cfg: &Config) -> Result<()> {
    let python = detect_python();
    let filtered: Vec<&str> = args.iter().copied().filter(|s| !s.is_empty()).collect();

    let status = std::process::Command::new(&python)
        .arg("archon.py")
        .args(&filtered)
        .status()
        .with_context(|| format!("Failed to launch Python at {python:?}"))?;

    std::process::exit(status.code().unwrap_or(1));
}

/// Returns the path to the Python executable to use.
fn detect_python() -> String {
    if std::path::Path::new(".venv/bin/python").exists() {
        return ".venv/bin/python".to_string();
    }
    "python3".to_string()
}

/// Locate the Tauri GUI binary if built.
fn find_tauri_binary() -> Option<PathBuf> {
    let candidate = PathBuf::from("ui-tauri")
        .join("src-tauri")
        .join("target")
        .join("release")
        .join("archon");
    if candidate.exists() {
        Some(candidate)
    } else {
        None
    }
}
