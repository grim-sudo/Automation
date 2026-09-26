/**
 * Automate page — single NL command execution with output log.
 * Mirrors archon/ui/gui/pages/automate_page.py.
 */

import { invoke } from "@tauri-apps/api/core";
import { toast }  from "../components/toast.js";

export function renderAutomate(container: HTMLElement): void {
  container.innerHTML = `
    <div class="topbar">
      <span class="topbar-title">🤖  Automate</span>
      <div class="topbar-spacer"></div>
      <button class="btn btn-ghost" id="clear-log">✕ Clear log</button>
    </div>
    <div style="padding:16px;display:flex;gap:8px;border-bottom:1px solid var(--border-subtle);
         background:var(--bg-surface);">
      <input id="cmd-input" type="text"
             placeholder="create a Python project named my-api"
             style="flex:1;" />
      <button class="btn btn-primary" id="cmd-run">▶ Run</button>
    </div>
    <div id="output-log" style="flex:1;overflow-y:auto;padding:16px;
         font-family:monospace;font-size:12px;color:var(--text-secondary);
         white-space:pre-wrap;"></div>
  `;

  const input  = container.querySelector<HTMLInputElement>("#cmd-input")!;
  const runBtn = container.querySelector<HTMLButtonElement>("#cmd-run")!;
  const log    = container.querySelector<HTMLElement>("#output-log")!;

  function logLine(text: string, color = "var(--text-secondary)"): void {
    const line = document.createElement("div");
    line.style.color = color;
    line.textContent = text;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  }

  async function runCommand(): Promise<void> {
    const cmd = input.value.trim();
    if (!cmd) return;
    runBtn.disabled = true;
    logLine(`$ ${cmd}`, "var(--purple-light)");

    try {
      const result = await invoke<string>("execute_command", { command: cmd });
      logLine(result, "var(--success)");
      toast.success("Command completed");
    } catch (err) {
      logLine(`  Error: ${err}`, "var(--error)");
      toast.error(String(err));
    } finally {
      runBtn.disabled = false;
    }
  }

  runBtn.addEventListener("click", runCommand);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); runCommand(); }
  });

  container.querySelector("#clear-log")!.addEventListener("click", () => {
    log.innerHTML = "";
  });
}
