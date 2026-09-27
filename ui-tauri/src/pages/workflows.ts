/**
 * Workflows — browse n8n workflows exposed by the Archon core. n8n is optional;
 * when it is not configured/loaded the call fails and we show an honest state.
 */

import { n8nListWorkflows, BackendUnavailable, type Workflow } from "../api.js";
import { el, panel, table, emptyState } from "../ui.js";

export function renderWorkflows(root: HTMLElement): void {
  const wrap = el("div", { class: "page-pad" });
  root.append(wrap);

  const p = panel("n8n Workflows");
  const host = el("div", { class: "table-scroll" });
  p.body.append(host);
  wrap.append(p.root);

  n8nListWorkflows()
    .then((wfs) => {
      if (!wfs.length) {
        p.body.replaceChildren(
          emptyState({
            glyph: "🔄",
            title: "No workflows",
            message: "n8n is reachable but reports no workflows.",
            state: "REAL",
          }),
        );
        return;
      }
      host.append(
        table(
          ["Name", "Status", "Trigger", "ID"],
          wfs.map((w: Workflow) => [
            w.name,
            statusBadge(w.active),
            String(w.trigger ?? "—"),
            w.id,
          ]),
        ),
      );
    })
    .catch((err) => {
      wrap.replaceChildren(
        emptyState({
          glyph: "🔄",
          title: "Workflows unavailable",
          message:
            err instanceof BackendUnavailable
              ? "Workflow data comes from the Archon core. Run Archon as a desktop app to see it."
              : "n8n is not configured or the bridge plugin is not loaded. Set the n8n URL and API key in Settings.",
          state: "UNAVAILABLE",
        }),
      );
    });
}

function statusBadge(active: boolean): HTMLElement {
  return el("span", {
    class: `wf-status ${active ? "wf-active" : "wf-idle"}`,
    text: active ? "active" : "idle",
  });
}
