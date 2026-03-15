/**
 * Distro Builder page — 5-step wizard.
 * Mirrors tyranos/ui/gui/pages/distro_page.py.
 */

import { invoke } from "@tauri-apps/api/core";
import { toast }  from "../components/toast.js";

type Step = "select" | "configure" | "confirm" | "building" | "done";

interface Profile { name: string; description: string; base: string; }

let selectedProfile = "";
let outputDir = "./distro_output";

export function renderDistro(container: HTMLElement): void {
  container.innerHTML = `
    <div class="topbar">
      <span class="topbar-title">🐧  Distro Builder</span>
      <div class="topbar-spacer"></div>
      <div id="step-indicator" style="font-size:12px;color:var(--text-secondary);"></div>
    </div>
    <div id="distro-content" style="flex:1;overflow-y:auto;padding:24px;"></div>
  `;

  showStep(container, "select");
}

function showStep(container: HTMLElement, step: Step): void {
  const content = container.querySelector<HTMLElement>("#distro-content")!;
  const indicator = container.querySelector<HTMLElement>("#step-indicator")!;

  const steps: Step[] = ["select", "configure", "confirm", "building", "done"];
  const idx = steps.indexOf(step) + 1;
  indicator.textContent = `Step ${idx} / ${steps.length}`;

  switch (step) {
    case "select":    renderSelectStep(container, content); break;
    case "configure": renderConfigureStep(container, content); break;
    case "confirm":   renderConfirmStep(container, content); break;
    case "building":  renderBuildingStep(container, content); break;
    case "done":      renderDoneStep(content); break;
  }
}

function renderSelectStep(container: HTMLElement, content: HTMLElement): void {
  content.innerHTML = `
    <h3 style="margin-bottom:16px;color:var(--text-accent);">Choose a distro profile</h3>
    <div id="profiles-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;">
      <div style="color:var(--text-secondary);">Loading profiles…</div>
    </div>
    <div style="margin-top:16px;">
      <p style="color:var(--text-secondary);font-size:12px;margin-bottom:8px;">
        Or describe your distro in plain English:
      </p>
      <div style="display:flex;gap:8px;">
        <input id="nl-desc" type="text" placeholder="minimal Arch with Wayland and development tools"
               style="flex:1;" />
        <button class="btn btn-primary" id="nl-go">Generate Profile</button>
      </div>
    </div>
  `;

  invoke<Profile[]>("distro_list_profiles").then((profiles) => {
    const grid = content.querySelector<HTMLElement>("#profiles-grid")!;
    grid.innerHTML = "";
    for (const p of profiles) {
      const card = document.createElement("div");
      card.className = "card";
      card.style.cssText = "cursor:pointer;transition:border-color 150ms;";
      card.innerHTML = `
        <div style="font-weight:600;margin-bottom:4px;">${p.name}</div>
        <div style="font-size:11px;color:var(--text-secondary);">${p.base}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">${p.description}</div>
      `;
      card.addEventListener("click", () => {
        selectedProfile = p.name;
        showStep(container, "configure");
      });
      grid.appendChild(card);
    }
  }).catch(() => {
    content.querySelector<HTMLElement>("#profiles-grid")!.innerHTML =
      `<div style="color:var(--error);">⚠ Could not load profiles. Is Tyranos installed?</div>`;
  });

  content.querySelector("#nl-go")!.addEventListener("click", () => {
    const desc = content.querySelector<HTMLInputElement>("#nl-desc")!.value.trim();
    if (!desc) return;
    selectedProfile = `nl:${desc}`;
    showStep(container, "configure");
  });
}

function renderConfigureStep(container: HTMLElement, content: HTMLElement): void {
  content.innerHTML = `
    <h3 style="margin-bottom:16px;color:var(--text-accent);">Configure build</h3>
    <p style="color:var(--text-secondary);margin-bottom:16px;">
      Profile: <strong style="color:var(--text-primary);">${selectedProfile}</strong>
    </p>
    <label style="font-size:12px;color:var(--text-secondary);">Output directory</label>
    <input id="output-dir" type="text" value="${outputDir}" style="margin-top:4px;margin-bottom:16px;" />
    <div style="display:flex;gap:8px;margin-top:8px;">
      <button class="btn btn-ghost" id="back-select">← Back</button>
      <button class="btn btn-primary" id="next-confirm">Continue →</button>
    </div>
  `;

  content.querySelector("#back-select")!.addEventListener("click", () =>
    showStep(container, "select"));
  content.querySelector("#next-confirm")!.addEventListener("click", () => {
    outputDir = content.querySelector<HTMLInputElement>("#output-dir")!.value.trim() || "./distro_output";
    showStep(container, "confirm");
  });
}

function renderConfirmStep(container: HTMLElement, content: HTMLElement): void {
  content.innerHTML = `
    <h3 style="margin-bottom:16px;color:var(--text-accent);">Confirm build</h3>
    <div class="card" style="margin-bottom:16px;">
      <div><strong>Profile:</strong> ${selectedProfile}</div>
      <div style="margin-top:6px;"><strong>Output:</strong> ${outputDir}</div>
      <div style="margin-top:12px;font-size:12px;color:var(--warning);">
        ⚠ Building a distro requires root access and may take 15–45 minutes.
      </div>
    </div>
    <div style="display:flex;gap:8px;">
      <button class="btn btn-ghost" id="back-configure">← Back</button>
      <button class="btn btn-primary" id="start-build">🔨 Start Build</button>
    </div>
  `;

  content.querySelector("#back-configure")!.addEventListener("click", () =>
    showStep(container, "configure"));
  content.querySelector("#start-build")!.addEventListener("click", () =>
    showStep(container, "building"));
}

function renderBuildingStep(container: HTMLElement, content: HTMLElement): void {
  content.innerHTML = `
    <h3 style="margin-bottom:16px;color:var(--text-accent);">Building…</h3>
    <div id="build-log" style="font-family:monospace;font-size:11px;color:var(--text-secondary);
         height:300px;overflow-y:auto;background:var(--bg-raised);padding:12px;
         border-radius:var(--radius-sm);border:1px solid var(--border-subtle);
         white-space:pre-wrap;"></div>
  `;

  const log = content.querySelector<HTMLElement>("#build-log")!;
  function logLine(msg: string): void {
    log.textContent += msg + "\n";
    log.scrollTop = log.scrollHeight;
  }

  logLine("[tyranos] Starting distro build…");
  logLine(`[tyranos] Profile: ${selectedProfile}`);
  logLine(`[tyranos] Output:  ${outputDir}`);

  invoke<string>("distro_build", { profile: selectedProfile, outputDir }).then((result) => {
    logLine(result);
    logLine("[tyranos] Build complete.");
    toast.success("Distro build finished!");
    showStep(container, "done");
  }).catch((err) => {
    logLine(`[error] ${err}`);
    toast.error("Build failed: " + String(err));
  });
}

function renderDoneStep(content: HTMLElement): void {
  content.innerHTML = `
    <div style="text-align:center;padding:40px;">
      <div style="font-size:48px;margin-bottom:16px;">✅</div>
      <h3 style="color:var(--success);margin-bottom:8px;">Build Complete!</h3>
      <p style="color:var(--text-secondary);">
        Your ISO has been written to <strong>${outputDir}</strong>.
      </p>
    </div>
  `;
}
