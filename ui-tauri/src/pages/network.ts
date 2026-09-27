/**
 * Network — interfaces with cumulative traffic and live throughput, read in
 * Rust. Rates are the per-refresh delta reported by `sysinfo`.
 */

import { networkInfo, BackendUnavailable, type InterfaceInfo } from "../api.js";
import { el, panel, table, emptyState, formatBytes, formatRate } from "../ui.js";

export function renderNetwork(root: HTMLElement): () => void {
  const wrap = el("div", { class: "page-pad" });
  root.append(wrap);

  const p = panel("Interfaces", { subtitle: "Throughput is the delta since the last refresh" });
  const host = el("div", { class: "table-scroll" });
  p.body.append(host);
  wrap.append(p.root);

  const paint = (ifaces: InterfaceInfo[]) => {
    const rows = ifaces.map((i) => [
      i.name,
      formatRate(i.rx_rate),
      formatRate(i.tx_rate),
      formatBytes(i.total_received),
      formatBytes(i.total_transmitted),
    ]);
    host.replaceChildren(table(["Interface", "↓ Rate", "↑ Rate", "↓ Total", "↑ Total"], rows));
  };

  let alive = true;
  const refresh = () => {
    networkInfo()
      .then(( i) => alive && paint(i))
      .catch((err) => {
        if (!alive) return;
        wrap.replaceChildren(
          emptyState({
            glyph: "⚠",
            title: "Network telemetry unavailable",
            message:
              err instanceof BackendUnavailable
                ? "Interface throughput is served by the Rust shell. Run Archon as a desktop app to see it."
                : String(err),
            state: "UNAVAILABLE",
          }),
        );
      });
  };
  refresh();
  const timer = window.setInterval(refresh, 2000);

  return () => {
    alive = false;
    window.clearInterval(timer);
  };
}
