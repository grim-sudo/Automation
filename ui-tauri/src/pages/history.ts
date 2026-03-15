/**
 * History page — execution log viewer.
 * Mirrors tyranos/ui/gui/pages/history_page.py.
 */

import { invoke } from "@tauri-apps/api/core";

interface HistoryEntry {
  id: string;
  command: string;
  status: "success" | "error" | "running";
  timestamp: string;
  output?: string;
}

export function renderHistory(container: HTMLElement): void {
  container.innerHTML = `
    <div class="topbar">
      <span class="topbar-title">📋  History</span>
      <div class="topbar-spacer"></div>
      <button class="btn btn-ghost" id="refresh-history">↻ Refresh</button>
    </div>
    <div style="flex:1;display:grid;grid-template-columns:300px 1fr;overflow:hidden;">
      <div id="history-list"
           style="border-right:1px solid var(--border-subtle);overflow-y:auto;padding:8px;">
        <div style="color:var(--text-secondary);text-align:center;padding:32px;font-size:12px;">
          Loading…
        </div>
      </div>
      <div id="history-detail"
           style="overflow-y:auto;padding:16px;font-family:monospace;font-size:12px;
           color:var(--text-secondary);white-space:pre-wrap;">
        Select an entry to view details.
      </div>
    </div>
  `;

  const listEl   = container.querySelector<HTMLElement>("#history-list")!;
  const detailEl = container.querySelector<HTMLElement>("#history-detail")!;

  function renderList(entries: HistoryEntry[]): void {
    listEl.innerHTML = "";
    if (!entries.length) {
      listEl.innerHTML = `<div style="color:var(--text-secondary);text-align:center;padding:32px;font-size:12px;">
        No history yet.</div>`;
      return;
    }
    for (const entry of entries) {
      const el = document.createElement("div");
      el.className = "card";
      el.style.cssText = "margin-bottom:6px;cursor:pointer;padding:8px 12px;";
      const statusColor =
        entry.status === "success" ? "var(--success)" :
        entry.status === "error"   ? "var(--error)"   : "var(--warning)";
      el.innerHTML = `
        <div style="font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;
             white-space:nowrap;color:var(--text-primary);">${entry.command}</div>
        <div style="font-size:10px;margin-top:3px;display:flex;gap:6px;">
          <span style="color:${statusColor};">${entry.status}</span>
          <span style="color:var(--text-muted);">${entry.timestamp}</span>
        </div>
      `;
      el.addEventListener("click", () => {
        detailEl.textContent = entry.output ?? "(no output)";
      });
      listEl.appendChild(el);
    }
  }

  async function loadHistory(): Promise<void> {
    try {
      const entries = await invoke<HistoryEntry[]>("get_history");
      renderList(entries);
    } catch {
      renderList([]);
    }
  }

  container.querySelector("#refresh-history")!.addEventListener("click", loadHistory);
  loadHistory();
}
