/**
 * Collapsible sidebar navigation component.
 * Mirrors archon/ui/gui/sidebar.py.
 */

import { showPage, type PageId } from "../router.js";

interface NavEntry {
  icon: string;
  label: string;
  page: PageId;
}

const NAV_ENTRIES: NavEntry[] = [
  { icon: "⚡", label: "Home",       page: "home"     },
  { icon: "💬", label: "Chat",       page: "chat"     },
  { icon: "🤖", label: "Automate",   page: "automate" },
  { icon: "🔄", label: "n8n",        page: "n8n"      },
  { icon: "🐧", label: "Distro",     page: "distro"   },
  { icon: "📋", label: "History",    page: "history"  },
  { icon: "⚙️",  label: "Settings",  page: "settings" },
];

export function initSidebar(): void {
  const sidebar = document.getElementById("sidebar")!;
  let collapsed = false;

  // Header
  const header = document.createElement("div");
  header.className = "sidebar-header";
  header.innerHTML = `
    <span class="sidebar-logo" id="sidebar-logo">⚡ Archon</span>
    <button class="btn btn-ghost" id="sidebar-toggle" title="Toggle sidebar"
            style="margin-left:auto;padding:4px 6px;">‹</button>
  `;
  sidebar.appendChild(header);

  // Nav
  const nav = document.createElement("nav");
  nav.className = "sidebar-nav";

  for (const entry of NAV_ENTRIES) {
    const btn = document.createElement("button");
    btn.className = "nav-item";
    btn.dataset.page = entry.page;
    btn.innerHTML = `
      <span class="nav-icon">${entry.icon}</span>
      <span class="nav-label">${entry.label}</span>
    `;
    btn.addEventListener("click", () => showPage(entry.page));
    nav.appendChild(btn);
  }
  sidebar.appendChild(nav);

  // Footer
  const footer = document.createElement("div");
  footer.className = "sidebar-footer";
  footer.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;">
      <div class="status-dot" id="status-dot"></div>
      <span class="nav-label" style="font-size:11px;color:var(--text-secondary)">Connected</span>
    </div>
  `;
  sidebar.appendChild(footer);

  // Toggle collapse
  document.getElementById("sidebar-toggle")!.addEventListener("click", () => {
    collapsed = !collapsed;
    sidebar.classList.toggle("collapsed", collapsed);
    const toggle = document.getElementById("sidebar-toggle")!;
    toggle.textContent = collapsed ? "›" : "‹";
  });
}
