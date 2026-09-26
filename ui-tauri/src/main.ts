/**
 * Archon GUI — Tauri frontend entry point.
 * Initialises the sidebar and routes to the correct page on load.
 */

import { initSidebar } from "./components/sidebar.js";
import { showPage } from "./router.js";

document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
  showPage("home");
});
