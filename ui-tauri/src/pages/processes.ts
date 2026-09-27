/**
 * Processes — a live process table for this machine (top by CPU), read in Rust.
 */

import { listProcesses, BackendUnavailable, type ProcessInfo } from "../api.js";
import { el, panel, table, emptyState, button } from "../ui.js";

type SortKey = "cpu" | "mem" | "name";

export function renderProcesses(root: HTMLElement): () => void {
  const wrap = el("div", { class: "page-pad" });
  root.append(wrap);

  let sort: SortKey = "cpu";
  let latest: ProcessInfo[] = [];

  const p = panel("Processes", {
    subtitle: "Top by CPU",
    actions: [
      button("CPU", "ghost", () => setSort("cpu")),
      button("Memory", "ghost", () => setSort("mem")),
      button("Name", "ghost", () => setSort("name")),
    ],
  });
  const host = el("div", { class: "table-scroll" });
  p.body.append(host);
  wrap.append(p.root);

  function setSort(k: SortKey) {
    sort = k;
    paint();
  }

  function paint() {
    const rows = [...latest]
      .sort((a, b) =>
        sort === "name" ? a.name.localeCompare(b.name) : b[sort === "cpu" ? "cpu" : "mem_percent"] - a[sort === "cpu" ? "cpu" : "mem_percent"],
      )
      .slice(0, 60)
      .map((pr) => [
        String(pr.pid),
        pr.name,
        `${pr.cpu.toFixed(1)}%`,
        `${pr.mem_percent.toFixed(1)}%`,
      ]);
    host.replaceChildren(table(["PID", "Process", "CPU", "Memory"], rows));
  }

  let alive = true;
  const refresh = () => {
    listProcesses()
      .then((ps) => {
        if (!alive) return;
        latest = ps;
        paint();
      })
      .catch((err) => {
        if (!alive) return;
        wrap.replaceChildren(
          emptyState({
            glyph: "⚠",
            title: "Process table unavailable",
            message:
              err instanceof BackendUnavailable
                ? "The live process table is served by the Rust shell. Run Archon as a desktop app to see it."
                : String(err),
            state: "UNAVAILABLE",
          }),
        );
      });
  };
  refresh();
  const timer = window.setInterval(refresh, 3000);

  return () => {
    alive = false;
    window.clearInterval(timer);
  };
}
