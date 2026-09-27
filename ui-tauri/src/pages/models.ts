/**
 * Models — the intelligence Archon routes tasks to. Reflects the live AI router
 * status from the Python core (provider, active model, key presence, fallbacks).
 */

import { aiStatus, BackendUnavailable, type AiStatus } from "../api.js";
import { el, panel, kv, emptyState, sectionLabel } from "../ui.js";

export function renderModels(root: HTMLElement): void {
  const wrap = el("div", { class: "page-pad models-grid" });
  root.append(wrap);

  const statusPanel = panel("Router Status");
  wrap.append(statusPanel.root);

  aiStatus()
    .then((s) => paint(wrap, statusPanel.body, s))
    .catch((err) => {
      wrap.className = "page-pad";
      wrap.replaceChildren(
        emptyState({
          glyph: "⚠",
          title: "AI status unavailable",
          message:
            err instanceof BackendUnavailable
              ? "AI router status comes from the Archon core. Run Archon as a desktop app to see it."
              : String(err),
          state: "UNAVAILABLE",
        }),
      );
    });
}

function paint(wrap: HTMLElement, body: HTMLElement, s: AiStatus): void {
  const online = s.available;
  const rows = {
    state: kv("State"),
    provider: kv("Provider"),
    model: kv("Active model"),
    key: kv("API key"),
  };
  rows.state.set(online ? "● Available" : "● Offline", online ? "var(--success)" : "var(--error)");
  rows.provider.set(s.provider || "—");
  rows.model.set(s.model || "—");
  rows.key.set(s.has_api_key ? "Present" : "Missing", s.has_api_key ? "var(--success)" : "var(--warning)");
  for (const r of Object.values(rows)) body.append(r.row);
  if (s.last_error) {
    body.append(el("div", { class: "inline-error", text: s.last_error }));
  }

  if (s.available_models?.length) {
    const listPanel = panel("Available Models", { subtitle: `${s.available_models.length} in fallback chain` });
    listPanel.body.append(sectionLabel("Fallback order"));
    const list = el("div", { class: "model-list" });
    s.available_models.forEach((m, i) =>
      list.append(
        el("div", { class: "model-item" }, [
          el("span", { class: "model-index", text: String(i + 1) }),
          el("span", { class: "model-name", text: m }),
          ...(m === s.model ? [el("span", { class: "model-active", text: "ACTIVE" })] : []),
        ]),
      ),
    );
    listPanel.body.append(list);
    wrap.append(listPanel.root);
  }
}
