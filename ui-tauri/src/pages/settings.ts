/**
 * Settings page — API keys, n8n URL, and preferences.
 * Mirrors tyranos/ui/gui/pages/settings_page.py.
 */

import { invoke } from "@tauri-apps/api/core";
import { toast }  from "../components/toast.js";

interface Settings {
  openrouter_api_key: string;
  n8n_url: string;
  n8n_api_key: string;
  debug: boolean;
  safe_mode: boolean;
}

export function renderSettings(container: HTMLElement): void {
  container.innerHTML = `
    <div class="topbar">
      <span class="topbar-title">⚙️  Settings</span>
      <div class="topbar-spacer"></div>
      <button class="btn btn-primary" id="save-settings">Save</button>
    </div>
    <div style="flex:1;overflow-y:auto;padding:24px;max-width:600px;">
      <h3 style="color:var(--text-accent);margin-bottom:16px;">AI Configuration</h3>
      <label style="font-size:12px;color:var(--text-secondary);">OpenRouter API Key</label>
      <input id="or-key" type="password" placeholder="sk-or-v1-…"
             style="margin-top:4px;margin-bottom:16px;" />

      <h3 style="color:var(--text-accent);margin:16px 0 16px;">n8n Integration</h3>
      <label style="font-size:12px;color:var(--text-secondary);">n8n URL</label>
      <input id="n8n-url" type="text" value="http://localhost:5678"
             style="margin-top:4px;margin-bottom:12px;" />
      <label style="font-size:12px;color:var(--text-secondary);">n8n API Key</label>
      <input id="n8n-key" type="password" placeholder="your-n8n-api-key"
             style="margin-top:4px;margin-bottom:16px;" />

      <h3 style="color:var(--text-accent);margin:16px 0 16px;">Behaviour</h3>
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <input type="checkbox" id="debug-mode" style="width:auto;" />
        <label for="debug-mode" style="font-size:13px;">Debug mode (verbose logging)</label>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <input type="checkbox" id="safe-mode" style="width:auto;" />
        <label for="safe-mode" style="font-size:13px;">Safe mode (confirm destructive ops)</label>
      </div>
    </div>
  `;

  invoke<Settings>("get_settings").then((s) => {
    (container.querySelector<HTMLInputElement>("#or-key")!).value   = s.openrouter_api_key;
    (container.querySelector<HTMLInputElement>("#n8n-url")!).value  = s.n8n_url;
    (container.querySelector<HTMLInputElement>("#n8n-key")!).value  = s.n8n_api_key;
    (container.querySelector<HTMLInputElement>("#debug-mode")!).checked = s.debug;
    (container.querySelector<HTMLInputElement>("#safe-mode")!).checked  = s.safe_mode;
  }).catch(() => {});

  container.querySelector("#save-settings")!.addEventListener("click", async () => {
    const settings: Settings = {
      openrouter_api_key: (container.querySelector<HTMLInputElement>("#or-key")!).value,
      n8n_url:            (container.querySelector<HTMLInputElement>("#n8n-url")!).value,
      n8n_api_key:        (container.querySelector<HTMLInputElement>("#n8n-key")!).value,
      debug:              (container.querySelector<HTMLInputElement>("#debug-mode")!).checked,
      safe_mode:          (container.querySelector<HTMLInputElement>("#safe-mode")!).checked,
    };
    try {
      await invoke("save_settings", { settings });
      toast.success("Settings saved.");
    } catch (err) { toast.error(String(err)); }
  });
}
