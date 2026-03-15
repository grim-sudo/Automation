/**
 * Simple hash-based page router.
 * Each page module exports a `render(container: HTMLElement) => void` function.
 */

import { renderHome }     from "./pages/home.js";
import { renderChat }     from "./pages/chat.js";
import { renderAutomate } from "./pages/automate.js";
import { renderN8n }      from "./pages/n8n.js";
import { renderDistro }   from "./pages/distro.js";
import { renderHistory }  from "./pages/history.js";
import { renderSettings } from "./pages/settings.js";

export type PageId =
  | "home" | "chat" | "automate" | "n8n"
  | "distro" | "history" | "settings";

const RENDERERS: Record<PageId, (el: HTMLElement) => void> = {
  home:     renderHome,
  chat:     renderChat,
  automate: renderAutomate,
  n8n:      renderN8n,
  distro:   renderDistro,
  history:  renderHistory,
  settings: renderSettings,
};

let _currentPage: PageId | null = null;

export function showPage(id: PageId): void {
  if (_currentPage === id) return;
  _currentPage = id;

  const content = document.getElementById("content")!;
  content.innerHTML = "";

  const container = document.createElement("div");
  container.className = "page active";
  content.appendChild(container);

  RENDERERS[id](container);

  // Update nav active state
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", (el as HTMLElement).dataset.page === id);
  });
}
