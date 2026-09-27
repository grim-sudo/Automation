/**
 * Standby views — capabilities the backend does not implement yet. Rather than
 * fake data, each renders an honest NOT IMPLEMENTED empty state describing what
 * the view will show once its backend exists.
 */

import { el, emptyState, panel } from "../ui.js";

const COPY: Record<string, { glyph: string; title: string; message: string }> = {
  agents: {
    glyph: "◇",
    title: "Agents",
    message:
      "Autonomous operations that Archon runs on your behalf will appear here — status, current step, and results. No agent runtime is wired to this build yet.",
  },
  memory: {
    glyph: "▤",
    title: "Memory",
    message:
      "What Archon knows about your environment and preferences will live here. There is no persistent memory store connected yet.",
  },
  projects: {
    glyph: "▦",
    title: "Projects",
    message:
      "Architecture, decisions, tasks, and generated artifacts for each project will be tracked here. No project store is connected yet.",
  },
  datasets: {
    glyph: "≋",
    title: "Datasets",
    message:
      "Query and summarize data as an instrument, not a spreadsheet. No dataset source is connected to this build yet.",
  },
  analytics: {
    glyph: "◔",
    title: "Analytics",
    message:
      "Aggregations and insights derived from Archon's operations will be shown here once a metrics backend is connected.",
  },
};

export function standby(key: string) {
  return (root: HTMLElement): void => {
    const meta = COPY[key] ?? { glyph: "○", title: key, message: "Not implemented yet." };
    const wrap = el("div", { class: "page-pad" });
    const p = panel(meta.title, { subtitle: "Awaiting backend" });
    p.body.append(
      emptyState({
        glyph: meta.glyph,
        title: "Not wired up",
        message: meta.message,
        state: "NOT_IMPLEMENTED",
      }),
    );
    wrap.append(p.root);
    root.append(wrap);
  };
}
