/**
 * Overview — a calm status summary: core state, host snapshot, capability count,
 * and AI router state. Reads the same real backends as the specialized views.
 */

import { systemInfo, describeCapabilities, aiStatus, BackendUnavailable } from "../api.js";
import { el, panel, kv, button, formatBytes, formatDuration } from "../ui.js";
import { showPage } from "../router.js";

export function renderOverview(root: HTMLElement): void {
  const wrap = el("div", { class: "page-pad overview-grid" });
  root.append(wrap);

  const core = panel("Archon Core", {
    actions: [button("Open Command", "ghost", () => showPage("command"))],
  });
  const coreState = kv("State", "checking…");
  const coreCaps = kv("Capabilities");
  const coreAi = kv("Intelligence");
  core.body.append(coreState.row, coreCaps.row, coreAi.row);

  const host = panel("Host", {
    actions: [button("Systems", "ghost", () => showPage("systems"))],
  });
  const hHost = kv("Hostname");
  const hOs = kv("OS");
  const hCpu = kv("CPU");
  const hMem = kv("Memory");
  const hUp = kv("Uptime");
  host.body.append(hHost.row, hOs.row, hCpu.row, hMem.row, hUp.row);

  wrap.append(core.root, host.root);

  systemInfo()
    .then((s) => {
      coreState.set("● Online", "var(--success)");
      hHost.set(s.host);
      hOs.set(s.os);
      hCpu.set(`${s.cpu_model} · ${s.cpu_usage.toFixed(0)}%`);
      hMem.set(`${formatBytes(s.mem_used)} / ${formatBytes(s.mem_total)}`);
      hUp.set(formatDuration(s.uptime_secs));
    })
    .catch((err) => {
      const off = err instanceof BackendUnavailable;
      coreState.set(off ? "● Offline" : "● Degraded", "var(--error)");
      for (const r of [hHost, hOs, hCpu, hMem, hUp]) r.set("—");
    });

  describeCapabilities()
    .then((c) => coreCaps.set(String(Object.keys(c).length)))
    .catch(() => coreCaps.set("—"));

  aiStatus()
    .then((a) =>
      coreAi.set(
        a.available ? `${a.provider ?? "router"} · ${a.model ?? "ready"}` : "offline",
        a.available ? "var(--success)" : "var(--warning)",
      ),
    )
    .catch(() => coreAi.set("—"));
}
