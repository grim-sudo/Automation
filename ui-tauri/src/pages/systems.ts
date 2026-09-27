/**
 * Systems — this machine's live hardware and health, read natively in Rust via
 * `sysinfo`. Polls on an interval; stops when the view is left.
 */

import { systemInfo, BackendUnavailable, type SystemInfo } from "../api.js";
import { el, panel, kv, meter, emptyState, formatBytes, formatDuration } from "../ui.js";

export function renderSystems(root: HTMLElement): () => void {
  const wrap = el("div", { class: "page-pad systems-grid" });
  root.append(wrap);

  const hostPanel = panel("Host");
  const hostKv = {
    host: kv("Hostname"),
    os: kv("OS"),
    kernel: kv("Kernel"),
    arch: kv("Architecture"),
    cpu: kv("CPU"),
    cores: kv("Cores / Threads"),
    uptime: kv("Uptime"),
  };
  for (const k of Object.values(hostKv)) hostPanel.body.append(k.row);

  const loadPanel = panel("Load");
  const cpuMeterHost = el("div", { class: "labeled-meter" });
  const ramMeterHost = el("div", { class: "labeled-meter" });
  loadPanel.body.append(cpuMeterHost, ramMeterHost);

  const disksPanel = panel("Disks");

  wrap.append(hostPanel.root, loadPanel.root, disksPanel.root);

  const paint = (s: SystemInfo) => {
    hostKv.host.set(s.host);
    hostKv.os.set(s.os);
    hostKv.kernel.set(s.kernel);
    hostKv.arch.set(s.arch);
    hostKv.cpu.set(s.cpu_model);
    hostKv.cores.set(`${s.cpu_cores} / ${s.cpu_threads}`);
    hostKv.uptime.set(formatDuration(s.uptime_secs));

    const ramPct = (s.mem_used / s.mem_total) * 100;
    cpuMeterHost.replaceChildren(
      labeledMeter("CPU", `${s.cpu_usage.toFixed(0)}%`, s.cpu_usage),
    );
    ramMeterHost.replaceChildren(
      labeledMeter(
        "Memory",
        `${formatBytes(s.mem_used)} / ${formatBytes(s.mem_total)}`,
        ramPct,
      ),
    );

    disksPanel.body.replaceChildren(
      ...s.disks.map((d) => {
        const used = ((d.total - d.available) / d.total) * 100;
        return el("div", { class: "labeled-meter" }, [
          labeledMeter(
            d.mount || d.name,
            `${formatBytes(d.total - d.available)} / ${formatBytes(d.total)}`,
            used,
          ),
        ]);
      }),
    );
  };

  let alive = true;
  const refresh = () => {
    systemInfo()
      .then((s) => alive && paint(s))
      .catch((err) => {
        if (!alive) return;
        showUnavailable(wrap, err);
      });
  };
  refresh();
  const timer = window.setInterval(refresh, 2500);

  return () => {
    alive = false;
    window.clearInterval(timer);
  };
}

function labeledMeter(label: string, value: string, pct: number): HTMLElement {
  return el("div", {}, [
    el("div", { class: "meter-row" }, [
      el("span", { class: "meter-label", text: label }),
      el("span", { class: "meter-value", text: value }),
    ]),
    meter(pct, "state"),
  ]);
}

function showUnavailable(wrap: HTMLElement, err: unknown): void {
  wrap.className = "page-pad";
  wrap.replaceChildren(
    emptyState({
      glyph: "⚠",
      title: "Telemetry unavailable",
      message:
        err instanceof BackendUnavailable
          ? "Live system telemetry is served by the Rust shell. Run Archon as a desktop app to see it."
          : String(err),
      state: "UNAVAILABLE",
    }),
  );
}
