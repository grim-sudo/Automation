/**
 * Settings — configuration surface. Archon reads its real configuration from
 * `config.toml` / environment at runtime; this build's IPC does not persist
 * edits back, so the view is informational and states that plainly rather than
 * pretending a save occurred.
 */

import { aiStatus, BackendUnavailable } from "../api.js";
import { el, panel, kv, emptyState, sectionLabel } from "../ui.js";

export function renderSettings(root: HTMLElement): void {
  const wrap = el("div", { class: "page-pad" });
  root.append(wrap);

  const p = panel("Configuration", { subtitle: "Read from config.toml and environment" });
  wrap.append(p.root);

  const provider = kv("AI provider");
  const model = kv("Active model");
  const key = kv("API key");
  p.body.append(provider.row, model.row, key.row);

  aiStatus()
    .then((s) => {
      provider.set(s.provider || "—");
      model.set(s.model || "—");
      key.set(s.has_api_key ? "Present" : "Missing", s.has_api_key ? "var(--success)" : "var(--warning)");
    })
    .catch((err) => {
      p.body.replaceChildren(
        emptyState({
          glyph: "⚙",
          title: "Configuration unavailable",
          message:
            err instanceof BackendUnavailable
              ? "Configuration is read by the Archon core. Run Archon as a desktop app to see it."
              : String(err),
          state: "UNAVAILABLE",
        }),
      );
    });

  p.body.append(sectionLabel("Editing"));
  p.body.append(
    el("div", {
      class: "note",
      text: "Configuration is edited in config.toml and the .env file, then reloaded by the core. The GUI reflects the active configuration; it does not write it back in this build.",
    }),
  );
}
