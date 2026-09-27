/**
 * Hash-free page router. Each page module exports `render(el)` and may return a
 * cleanup function (used to stop polling/animation loops when leaving a view).
 */

import type { PageId } from "./nav.js";
import { setActiveNav } from "./components/sidebar.js";
import { setTopBarPage } from "./components/topbar.js";

import { renderCommand } from "./pages/command.js";
import { renderOverview } from "./pages/overview.js";
import { renderChat } from "./pages/chat.js";
import { renderSystems } from "./pages/systems.js";
import { renderProcesses } from "./pages/processes.js";
import { renderFiles } from "./pages/files.js";
import { renderNetwork } from "./pages/network.js";
import { renderModels } from "./pages/models.js";
import { renderWorkflows } from "./pages/workflows.js";
import { renderMcp } from "./pages/mcp.js";
import { renderOsBuilder } from "./pages/osbuilder.js";
import { renderLogs } from "./pages/logs.js";
import { renderSettings } from "./pages/settings.js";
import { standby } from "./pages/standby.js";

export type Cleanup = void | (() => void);
type Renderer = (el: HTMLElement) => Cleanup;

const RENDERERS: Record<PageId, Renderer> = {
  command: renderCommand,
  overview: renderOverview,
  chat: renderChat,
  systems: renderSystems,
  processes: renderProcesses,
  files: renderFiles,
  network: renderNetwork,
  models: renderModels,
  agents: standby("agents"),
  memory: standby("memory"),
  workflows: renderWorkflows,
  mcp: renderMcp,
  osbuilder: renderOsBuilder,
  projects: standby("projects"),
  datasets: standby("datasets"),
  analytics: standby("analytics"),
  logs: renderLogs,
  settings: renderSettings,
};

let current: PageId | null = null;
let cleanup: Cleanup = undefined;

export function showPage(id: PageId): void {
  if (id === current) return;
  if (typeof cleanup === "function") cleanup();

  const content = document.getElementById("content")!;
  content.innerHTML = "";
  const page = document.createElement("div");
  page.className = "page active";
  content.append(page);

  current = id;
  setActiveNav(id);
  setTopBarPage(id);
  cleanup = RENDERERS[id](page);
}
