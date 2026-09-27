/**
 * Archon command center — Tauri frontend entry point.
 * Mounts the sidebar and top bar, then routes to the Command view.
 */

import { initSidebar, setSidebarStatus } from "./components/sidebar.js";
import { initTopBar, setTopBarStatus } from "./components/topbar.js";
import { showPage } from "./router.js";
import { systemInfo, HAS_BACKEND } from "./api.js";

document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
  initTopBar();
  showPage("command");

  // Reflect real core reachability in the status indicators.
  const probe = () => {
    systemInfo()
      .then(() => {
        setSidebarStatus(true);
        setTopBarStatus(true);
      })
      .catch(() => {
        setSidebarStatus(false, HAS_BACKEND ? "Core Degraded" : "No Backend");
        setTopBarStatus(false, HAS_BACKEND ? "DEGRADED" : "NO BACKEND");
      });
  };
  probe();
  window.setInterval(probe, 5000);
});
