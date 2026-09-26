/**
 * Home / Dashboard page — mirrors archon/ui/gui/pages/home_page.py.
 */

import { showPage } from "../router.js";

export function renderHome(container: HTMLElement): void {
  container.innerHTML = `
    <div class="topbar">
      <span class="topbar-title">⚡  Dashboard</span>
      <div class="topbar-spacer"></div>
      <span style="font-size:11px;color:var(--text-secondary)">Archon v2.0</span>
    </div>
    <div style="flex:1;overflow-y:auto;padding:20px;display:grid;
                grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
                gap:16px;align-content:start;">

      <div class="card" style="grid-column:1/-1;">
        <h2 style="color:var(--text-accent);margin-bottom:8px;font-size:22px;">
          Universal Automation Intelligence
        </h2>
        <p style="color:var(--text-secondary);line-height:1.6;">
          Describe what you want in plain English. Archon maps your intent through
          a multi-layer AI pipeline and runs it.
        </p>
        <div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;">
          <button class="btn btn-primary" data-nav="chat">💬 Start Chatting</button>
          <button class="btn btn-ghost"   data-nav="automate">🤖 Run Command</button>
        </div>
      </div>

      ${quickCard("💬", "Chat", "Multi-turn AI conversation with streaming output.", "chat")}
      ${quickCard("🤖", "Automate", "Execute natural-language automation commands.", "automate")}
      ${quickCard("🔄", "n8n", "Browse, trigger, and manage n8n workflows.", "n8n")}
      ${quickCard("🐧", "Distro Builder", "Build bootable Linux ISOs from TOML profiles.", "distro")}
      ${quickCard("📋", "History", "View past executions and their outputs.", "history")}
      ${quickCard("⚙️", "Settings", "Configure AI keys, n8n URL, and preferences.", "settings")}
    </div>
  `;

  container.querySelectorAll("[data-nav]").forEach((btn) => {
    btn.addEventListener("click", () => {
      showPage((btn as HTMLElement).dataset.nav as any);
    });
  });
}

function quickCard(icon: string, title: string, desc: string, page: string): string {
  return `
    <div class="card" style="cursor:pointer;" data-nav="${page}">
      <div style="font-size:24px;margin-bottom:8px;">${icon}</div>
      <div style="font-weight:600;color:var(--text-primary);margin-bottom:4px;">${title}</div>
      <div style="font-size:12px;color:var(--text-secondary);">${desc}</div>
    </div>
  `;
}
