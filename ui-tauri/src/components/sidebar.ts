/**
 * Grouped sidebar navigation with monochrome line icons and a status footer.
 * Mirrors archon/ui/gui/sidebar.py.
 */

import { NAV_GROUPS, icon, type PageId } from "../nav.js";
import { el } from "../ui.js";
import { showPage } from "../router.js";

let buttons: Map<PageId, HTMLElement> = new Map();

export function initSidebar(): void {
  const sidebar = document.getElementById("sidebar")!;
  sidebar.innerHTML = "";
  buttons = new Map();

  // Logo / header.
  const logo = el("div", { class: "sidebar-header" }, [
    el("div", { class: "sidebar-mark", html: archonMark() }),
    el("span", { class: "sidebar-logo", text: "ARCHON" }),
  ]);
  sidebar.append(logo);

  // Grouped nav.
  const nav = el("nav", { class: "sidebar-nav" });
  for (const group of NAV_GROUPS) {
    nav.append(el("div", { class: "nav-group-title", text: group.title }));
    for (const item of group.items) {
      const btn = el("button", { class: "nav-item", "data-page": item.page }, [
        el("span", { class: "nav-accent" }),
        el("span", { class: "nav-icon" }, [icon(item.icon, 18)]),
        el("span", { class: "nav-label", text: item.label }),
      ]);
      btn.addEventListener("click", () => showPage(item.page));
      buttons.set(item.page, btn);
      nav.append(btn);
    }
  }
  sidebar.append(nav);

  // Status footer.
  sidebar.append(
    el("div", { class: "sidebar-footer" }, [
      el("span", { class: "status-dot", id: "sidebar-status-dot" }),
      el("span", { class: "sidebar-status", id: "sidebar-status", text: "System Online" }),
      el("span", { class: "sidebar-version", text: "v2.0.0" }),
    ]),
  );
}

export function setActiveNav(page: PageId): void {
  buttons.forEach((btn, key) => btn.classList.toggle("active", key === page));
}

export function setSidebarStatus(online: boolean, label?: string): void {
  const dot = document.getElementById("sidebar-status-dot");
  const text = document.getElementById("sidebar-status");
  const color = online ? "var(--success)" : "var(--error)";
  if (dot) dot.style.background = color;
  if (text) {
    text.textContent = label ?? (online ? "System Online" : "Core Offline");
    text.style.color = color;
  }
}

/** Static Archon diamond emblem as inline SVG. */
function archonMark(): string {
  return `<svg viewBox="0 0 24 24" width="26" height="26" fill="none">
    <path d="M12 2l9 10-9 10-9-10z" stroke="var(--gold)" stroke-width="1.4"/>
    <path d="M12 7l4.5 5-4.5 5-4.5-5z" fill="var(--gold)" opacity="0.9"/>
  </svg>`;
}
