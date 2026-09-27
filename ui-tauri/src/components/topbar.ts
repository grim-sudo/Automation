/**
 * TopBar — page context, a global command entry that hands off to the Command
 * view, and a compact status pill. Mirrors archon/ui/gui/components/topbar.py.
 */

import { PAGE_META, type PageId } from "../nav.js";
import { el } from "../ui.js";
import { showPage } from "../router.js";
import { runCommand } from "../pages/command.js";

export function initTopBar(): void {
  const bar = document.getElementById("topbar")!;
  bar.innerHTML = "";

  const title = el("div", { class: "topbar-title", id: "topbar-title", text: "Command" });
  const context = el("div", { class: "topbar-context", id: "topbar-context", text: "" });
  bar.append(el("div", { class: "topbar-left" }, [title, context]));

  const entry = el("input", {
    type: "text",
    class: "topbar-command",
    id: "topbar-command",
    placeholder: "⌘  Run a command…",
  }) as HTMLInputElement;
  entry.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && entry.value.trim()) {
      const text = entry.value.trim();
      entry.value = "";
      showPage("command");
      runCommand(text);
    }
  });
  bar.append(el("div", { class: "topbar-center" }, [entry]));

  const pill = el("div", { class: "status-pill", id: "topbar-status-pill" }, [
    el("span", { class: "status-dot" }),
    el("span", { class: "status-pill-text", id: "topbar-status-text", text: "ONLINE" }),
  ]);
  const settings = el("button", { class: "btn btn-ghost btn-icon", title: "Settings", text: "⚙" });
  settings.addEventListener("click", () => showPage("settings"));
  bar.append(el("div", { class: "topbar-right" }, [pill, settings]));
}

export function setTopBarPage(page: PageId): void {
  const [title, context] = PAGE_META[page];
  const t = document.getElementById("topbar-title");
  const c = document.getElementById("topbar-context");
  if (t) t.textContent = title;
  if (c) c.textContent = context;
}

export function setTopBarStatus(online: boolean, label?: string): void {
  const pill = document.getElementById("topbar-status-pill");
  const text = document.getElementById("topbar-status-text");
  if (pill) pill.classList.toggle("offline", !online);
  if (text) text.textContent = label ?? (online ? "ONLINE" : "OFFLINE");
}
