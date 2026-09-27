/**
 * MCP — the capability registry that extends Archon's reach. Renders the real
 * registry from the Python core (capabilities, their risk, and their actions).
 */

import { describeCapabilities, BackendUnavailable, type Capabilities } from "../api.js";
import { el, panel, emptyState, dataBadge } from "../ui.js";

const RISK_TONE: Record<string, string> = {
  low: "risk-low",
  medium: "risk-medium",
  high: "risk-high",
};

export function renderMcp(root: HTMLElement): void {
  const wrap = el("div", { class: "page-pad" });
  root.append(wrap);

  describeCapabilities()
    .then((caps) => paint(wrap, caps))
    .catch((err) => {
      wrap.replaceChildren(
        emptyState({
          glyph: "⚠",
          title: "Capability registry unavailable",
          message:
            err instanceof BackendUnavailable
              ? "The capability registry comes from the Archon core. Run Archon as a desktop app to see it."
              : String(err),
          state: "UNAVAILABLE",
        }),
      );
    });
}

function paint(wrap: HTMLElement, caps: Capabilities): void {
  const names = Object.keys(caps);
  if (names.length === 0) {
    wrap.append(
      emptyState({
        glyph: "◇",
        title: "No capabilities loaded",
        message: "The registry returned no capabilities. Optional plugins may be missing.",
        state: "REAL",
      }),
    );
    return;
  }

  const header = el("div", { class: "mcp-header" }, [
    el("span", { text: `${names.length} capabilities registered` }),
    dataBadge("REAL"),
  ]);
  wrap.append(header);

  const grid = el("div", { class: "capability-grid" });
  for (const name of names) {
    const cap = caps[name];
    const p = panel(name, { subtitle: cap.description });
    p.body.append(
      el("div", { class: "cap-risk" }, [
        el("span", { class: `risk-badge ${RISK_TONE[cap.risk] ?? "risk-low"}`, text: `risk: ${cap.risk}` }),
        el("span", { class: "cap-count", text: `${cap.actions.length} actions` }),
      ]),
    );
    const actions = el("div", { class: "action-list" });
    for (const a of cap.actions) {
      actions.append(
        el("div", { class: "action-row" }, [
          el("span", { class: "action-name", text: a.name }),
          el("span", { class: `risk-dot ${RISK_TONE[a.risk] ?? "risk-low"}`, title: `risk: ${a.risk}` }),
          el("span", { class: "action-desc", text: a.description }),
        ]),
      );
    }
    p.body.append(actions);
    grid.append(p.root);
  }
  wrap.append(grid);
}
