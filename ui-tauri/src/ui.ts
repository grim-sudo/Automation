/**
 * Small DOM + formatting helpers shared across views. Deliberately dependency
 * free — the command center is plain TypeScript over the design-system CSS.
 */

type Attrs = Record<string, string | number | boolean | undefined>;

/** Create an element with attributes and children in one call. */
export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Attrs = {},
  children: (Node | string)[] = [],
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === false) continue;
    if (k === "class") node.className = String(v);
    else if (k === "text") node.textContent = String(v);
    else if (k === "html") node.innerHTML = String(v);
    else if (k.startsWith("data-")) node.setAttribute(k, String(v));
    else node.setAttribute(k, String(v));
  }
  for (const c of children) node.append(c);
  return node;
}

/** A titled panel — a bordered surface, the primary layout unit. */
export function panel(title: string, opts: { subtitle?: string; actions?: HTMLElement[] } = {}) {
  const head = el("div", { class: "panel-head" }, [
    el("div", { class: "panel-titles" }, [
      el("div", { class: "panel-title", text: title }),
      ...(opts.subtitle ? [el("div", { class: "panel-subtitle", text: opts.subtitle })] : []),
    ]),
  ]);
  if (opts.actions?.length) {
    head.append(el("div", { class: "panel-actions" }, opts.actions));
  }
  const body = el("div", { class: "panel-body" });
  const root = el("section", { class: "panel" }, [head, body]);
  return { root, body };
}

/** Small section label (uppercased). */
export function sectionLabel(text: string) {
  return el("div", { class: "section-label", text });
}

/** A key → value readout row. */
export function kv(key: string, value = "—") {
  const val = el("span", { class: "kv-value", text: value });
  const row = el("div", { class: "kv-row" }, [el("span", { class: "kv-key", text: key }), val]);
  return {
    row,
    set(v: string, color?: string) {
      val.textContent = v;
      val.style.color = color ?? "";
    },
  };
}

/** Data-honesty badge: is this view showing REAL data, or not? */
export type DataState = "REAL" | "UNAVAILABLE" | "NOT_IMPLEMENTED";
export function dataBadge(state: DataState) {
  const label = state === "NOT_IMPLEMENTED" ? "NOT IMPLEMENTED" : state;
  return el("span", { class: `data-badge data-${state.toLowerCase()}`, text: label });
}

/** Centered empty / unavailable state with an icon glyph and message. */
export function emptyState(opts: {
  glyph?: string;
  title: string;
  message: string;
  state?: DataState;
  action?: HTMLElement;
}) {
  return el("div", { class: "empty-state" }, [
    ...(opts.glyph ? [el("div", { class: "empty-glyph", text: opts.glyph })] : []),
    el("div", { class: "empty-title" }, [
      document.createTextNode(opts.title),
      ...(opts.state ? [dataBadge(opts.state)] : []),
    ]),
    el("div", { class: "empty-message", text: opts.message }),
    ...(opts.action ? [opts.action] : []),
  ]);
}

/** A simple table from headers + string cell rows. */
export function table(headers: string[], rows: (string | HTMLElement)[][]) {
  const thead = el("thead", {}, [
    el("tr", {}, headers.map((h) => el("th", { text: h }))),
  ]);
  const tbody = el("tbody", {}, rows.map((r) =>
    el("tr", {}, r.map((c) =>
      el("td", {}, [typeof c === "string" ? document.createTextNode(c) : c]))),
  ));
  return el("table", { class: "data-table" }, [thead, tbody]);
}

/** A thin horizontal meter (0–100). */
export function meter(percent: number, tone: "gold" | "cyan" | "state" = "gold") {
  const p = Math.max(0, Math.min(100, percent));
  const cls = tone === "state"
    ? p > 85 ? "meter-error" : p > 60 ? "meter-warn" : "meter-ok"
    : `meter-${tone}`;
  const fill = el("div", { class: `meter-fill ${cls}` });
  fill.style.width = `${p}%`;
  return el("div", { class: "meter" }, [fill]);
}

/** Button helper. */
export function button(label: string, kind: "primary" | "ghost" = "ghost", onClick?: () => void) {
  const b = el("button", { class: `btn btn-${kind}`, text: label });
  if (onClick) b.addEventListener("click", onClick);
  return b;
}

// ── Formatting ──────────────────────────────────────────────────────────────

export function formatBytes(n: number): string {
  if (n <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  const i = Math.min(units.length - 1, Math.floor(Math.log(n) / Math.log(1024)));
  return `${(n / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function formatRate(bytesPerTick: number): string {
  return `${formatBytes(bytesPerTick)}/s`;
}

export function formatDuration(secs: number): string {
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}
