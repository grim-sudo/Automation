/**
 * Logs — past operations and their results from the Archon core.
 *
 * Honesty note: execution history is in-memory in the Python core, and the IPC
 * bridge spawns a fresh Python process per request, so history does not persist
 * across calls in this build. The view states that plainly when empty.
 */

import { getHistory, BackendUnavailable, type HistoryEntry } from "../api.js";
import { el, panel, table, emptyState } from "../ui.js";

export function renderLogs(root: HTMLElement): void {
  const wrap = el("div", { class: "page-pad" });
  root.append(wrap);

  const p = panel("Execution History");
  const host = el("div", { class: "table-scroll" });
  p.body.append(host);
  wrap.append(p.root);

  getHistory()
    .then((entries) => {
      if (!entries.length) {
        p.body.replaceChildren(
          emptyState({
            glyph: "▤",
            title: "No history in this session",
            message:
              "Execution history is kept in memory by the Archon core. Because each request runs in a fresh process, past operations are not retained here between calls.",
            state: "REAL",
          }),
        );
        return;
      }
      host.append(
        table(
          ["Time", "Command", "Result", "Status"],
          entries.map((e: HistoryEntry) => [
            str(e.timestamp),
            str(e.original_command),
            str(e.result_summary),
            statusBadge(e.success === true),
          ]),
        ),
      );
    })
    .catch((err) => {
      wrap.replaceChildren(
        emptyState({
          glyph: "⚠",
          title: "History unavailable",
          message:
            err instanceof BackendUnavailable
              ? "History comes from the Archon core. Run Archon as a desktop app to see it."
              : String(err),
          state: "UNAVAILABLE",
        }),
      );
    });
}

function str(v: unknown): string {
  return v === undefined || v === null ? "—" : String(v);
}

function statusBadge(ok: boolean): HTMLElement {
  return el("span", {
    class: `wf-status ${ok ? "wf-active" : "wf-idle"}`,
    text: ok ? "ok" : "failed",
  });
}
