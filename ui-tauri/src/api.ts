/**
 * Typed bridge to the Rust/Python backend.
 *
 * Live host telemetry (system / processes / network / filesystem) is served
 * natively by the Rust shell via `sysinfo` + `std::fs`. Everything that needs
 * Archon's brain (chat, capabilities, AI status, workflows, distro, history)
 * is forwarded by Rust to `python archon.py --tauri-ipc`.
 *
 * When the frontend runs outside a Tauri window (e.g. `vite dev` in a plain
 * browser) there is no backend. Rather than fabricate numbers, calls reject
 * with {@link BackendUnavailable} and views render an honest UNAVAILABLE state.
 */

type InvokeFn = (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;

function getInvoke(): InvokeFn | null {
  const t = (window as unknown as { __TAURI__?: { core?: { invoke?: InvokeFn } } }).__TAURI__;
  if (t && t.core && typeof t.core.invoke === "function") return t.core.invoke;
  return null;
}

/** True when a Tauri backend is present to answer commands. */
export const HAS_BACKEND = getInvoke() !== null;

/** Raised when no backend is reachable — surfaced to the UI as UNAVAILABLE. */
export class BackendUnavailable extends Error {
  constructor() {
    super("Backend unavailable — Archon core is not running.");
    this.name = "BackendUnavailable";
  }
}

async function call<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  const invoke = getInvoke();
  if (!invoke) throw new BackendUnavailable();
  return invoke(cmd, args) as Promise<T>;
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DiskInfo {
  name: string;
  mount: string;
  total: number;
  available: number;
}

export interface SystemInfo {
  host: string;
  os: string;
  kernel: string;
  arch: string;
  cpu_model: string;
  cpu_cores: number;
  cpu_threads: number;
  cpu_usage: number;
  mem_total: number;
  mem_used: number;
  uptime_secs: number;
  disks: DiskInfo[];
}

export interface ProcessInfo {
  pid: number;
  name: string;
  cpu: number;
  mem_percent: number;
}

export interface InterfaceInfo {
  name: string;
  total_received: number;
  total_transmitted: number;
  rx_rate: number;
  tx_rate: number;
}

export interface DirEntryInfo {
  name: string;
  path: string;
  is_dir: boolean;
  size: number;
}

export interface DirListing {
  path: string;
  parent: string | null;
  entries: DirEntryInfo[];
}

export interface CapabilityAction {
  name: string;
  risk: string;
  description: string;
}

export interface Capability {
  description: string;
  risk: string;
  actions: CapabilityAction[];
}

export type Capabilities = Record<string, Capability>;

export interface AiStatus {
  available: boolean;
  has_api_key: boolean;
  model: string | null;
  provider: string | null;
  last_error: string | null;
  available_models: string[];
}

export interface ChatResult {
  kind?: "conversation" | "automation";
  success?: boolean;
  reply?: string;
  result?: string;
  error?: string;
  [key: string]: unknown;
}

export type HistoryEntry = Record<string, unknown>;

export interface Workflow {
  id: string;
  name: string;
  active: boolean;
  trigger?: string | null;
  [key: string]: unknown;
}

// ── Rust-native telemetry (no Python spawn) ─────────────────────────────────────

export const systemInfo = () => call<SystemInfo>("system_info");
export const listProcesses = () => call<ProcessInfo[]>("list_processes");
export const networkInfo = () => call<InterfaceInfo[]>("network_info");
export const listDir = (path?: string) => call<DirListing>("list_dir", { path: path ?? null });

// ── Python-backed intelligence ──────────────────────────────────────────────────

export function sendMessage(message: string, history: { role: string; content: string }[] = []) {
  return call<string>("send_message", { message, history }).then(parseMaybeJson<ChatResult>);
}

export function executeCommand(command: string) {
  return call<string>("execute_command", { command }).then(parseMaybeJson<ChatResult>);
}

export const describeCapabilities = () => call<Capabilities>("describe_capabilities");
export const aiStatus = () => call<AiStatus>("ai_status");
export const getHistory = () => call<HistoryEntry[]>("get_history");
export const n8nListWorkflows = () => call<Workflow[]>("n8n_list_workflows");
export const distroListProfiles = () => call<string[]>("distro_list_profiles");
export const getFreeModels = () => call<Record<string, string>[]>("get_free_models");

/** Some Python actions return a JSON string; parse it, else wrap as reply. */
function parseMaybeJson<T>(raw: string): T {
  try {
    return JSON.parse(raw) as T;
  } catch {
    return { reply: raw } as unknown as T;
  }
}
