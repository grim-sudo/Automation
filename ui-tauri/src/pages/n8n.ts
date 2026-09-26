/**
 * n8n Workflows page — list, create, and trigger workflows.
 * Mirrors archon/ui/gui/pages/n8n_page.py.
 */

import { invoke } from "@tauri-apps/api/core";
import { toast }  from "../components/toast.js";

interface Workflow {
  id: string;
  name: string;
  active: boolean;
  trigger?: string;
  executionCount?: number;
}

export function renderN8n(container: HTMLElement): void {
  container.innerHTML = `
    <div class="topbar">
      <span class="topbar-title">🔄  n8n Workflows</span>
      <div class="topbar-spacer"></div>
      <button class="btn btn-ghost" id="refresh-wf">↻ Refresh</button>
      <button class="btn btn-primary" id="new-wf">+ New Workflow</button>
    </div>
    <div style="flex:1;display:grid;grid-template-columns:2fr 1fr;overflow:hidden;">
      <div style="display:flex;flex-direction:column;border-right:1px solid var(--border-subtle);overflow:hidden;">
        <div style="padding:12px 16px;border-bottom:1px solid var(--border-subtle);">
          <input id="wf-search" type="text" placeholder="🔍  Search workflows…" style="width:100%;" />
        </div>
        <div id="wf-list" style="flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:6px;">
          <div style="color:var(--text-secondary);text-align:center;padding:32px;">Loading…</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;overflow:hidden;">
        <div style="padding:12px 16px;border-bottom:1px solid var(--border-subtle);
             font-size:13px;font-weight:600;color:var(--text-accent);">📊 Execution Log</div>
        <div id="exec-log" style="flex:1;overflow-y:auto;padding:12px;">
          <div style="color:var(--text-secondary);text-align:center;padding:32px;font-size:12px;">
            Trigger a workflow to see execution output.
          </div>
        </div>
      </div>
    </div>

    <!-- Create drawer (hidden by default) -->
    <div id="create-drawer" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);
         z-index:100;align-items:center;justify-content:center;">
      <div class="card" style="width:440px;">
        <h3 style="margin-bottom:16px;">Create n8n Workflow</h3>
        <label style="font-size:12px;color:var(--text-secondary);">Workflow name</label>
        <input id="new-wf-name" type="text" placeholder="My Workflow" style="margin-top:4px;margin-bottom:12px;" />
        <label style="font-size:12px;color:var(--text-secondary);">Description (optional)</label>
        <textarea id="new-wf-desc" rows="3" placeholder="What does this workflow do?"
                  style="margin-top:4px;margin-bottom:16px;resize:vertical;"></textarea>
        <div style="display:flex;justify-content:space-between;">
          <button class="btn btn-ghost" id="cancel-create">Cancel</button>
          <button class="btn btn-primary" id="confirm-create">Create</button>
        </div>
      </div>
    </div>
  `;

  let allWorkflows: Workflow[] = [];

  const wfList    = container.querySelector<HTMLElement>("#wf-list")!;
  const execLog   = container.querySelector<HTMLElement>("#exec-log")!;
  const search    = container.querySelector<HTMLInputElement>("#wf-search")!;
  const drawer    = container.querySelector<HTMLElement>("#create-drawer")!;

  function renderWorkflows(wfs: Workflow[]): void {
    wfList.innerHTML = "";
    if (!wfs.length) {
      wfList.innerHTML = `<div style="color:var(--text-secondary);text-align:center;padding:32px;font-size:12px;">
        No workflows found. Create one or check your n8n connection in Settings.</div>`;
      return;
    }
    for (const wf of wfs) {
      const card = document.createElement("div");
      card.className = "card";
      card.style.cssText = "padding:10px 14px;display:flex;align-items:center;gap:10px;cursor:pointer;";
      card.innerHTML = `
        <div style="flex:1;">
          <div style="font-weight:600;font-size:13px;">${wf.name}</div>
          <div style="font-size:11px;color:var(--text-secondary);">
            ${wf.active ? "🟢 Active" : "⚫ Inactive"} · ${wf.executionCount ?? 0} runs
          </div>
        </div>
        <button class="btn btn-primary" style="font-size:11px;padding:4px 8px;">▶ Run</button>
      `;
      card.querySelector("button")!.addEventListener("click", (e) => {
        e.stopPropagation();
        triggerWorkflow(wf);
      });
      wfList.appendChild(card);
    }
  }

  async function loadWorkflows(): Promise<void> {
    wfList.innerHTML = `<div style="color:var(--text-secondary);text-align:center;padding:32px;">Loading…</div>`;
    try {
      allWorkflows = await invoke<Workflow[]>("n8n_list_workflows");
      renderWorkflows(allWorkflows);
    } catch (err) {
      wfList.innerHTML = `<div style="color:var(--error);text-align:center;padding:32px;font-size:12px;">
        ⚠ ${err}<br><br>Check n8n URL and API key in Settings.</div>`;
    }
  }

  async function triggerWorkflow(wf: Workflow): Promise<void> {
    try {
      const result = await invoke<string>("n8n_trigger_workflow", { id: wf.id });
      execLog.innerHTML = `
        <div class="card" style="padding:8px 12px;margin-bottom:8px;border-color:var(--success);">
          <div style="color:var(--success);font-size:13px;font-weight:600;">✓ ${wf.name}</div>
        </div>
        <div style="font-size:12px;color:var(--text-primary);word-break:break-all;">${result}</div>
      `;
      toast.success(`Triggered: ${wf.name}`);
    } catch (err) {
      execLog.innerHTML = `
        <div class="card" style="padding:8px 12px;border-color:var(--error);">
          <div style="color:var(--error);font-size:13px;font-weight:600;">✗ ${wf.name}</div>
        </div>
        <div style="font-size:12px;color:var(--error);margin-top:8px;">${err}</div>
      `;
      toast.error(String(err));
    }
  }

  search.addEventListener("input", () => {
    const q = search.value.toLowerCase();
    renderWorkflows(q ? allWorkflows.filter(w => w.name.toLowerCase().includes(q)) : allWorkflows);
  });

  container.querySelector("#refresh-wf")!.addEventListener("click", loadWorkflows);
  container.querySelector("#new-wf")!.addEventListener("click", () => {
    drawer.style.display = "flex";
  });
  container.querySelector("#cancel-create")!.addEventListener("click", () => {
    drawer.style.display = "none";
  });
  container.querySelector("#confirm-create")!.addEventListener("click", async () => {
    const name = (container.querySelector<HTMLInputElement>("#new-wf-name")!).value.trim();
    const desc = (container.querySelector<HTMLTextAreaElement>("#new-wf-desc")!).value.trim();
    if (!name) return;
    drawer.style.display = "none";
    try {
      await invoke("n8n_create_workflow", { name, description: desc });
      toast.success(`Created workflow: ${name}`);
      loadWorkflows();
    } catch (err) { toast.error(String(err)); }
  });

  loadWorkflows();
}
