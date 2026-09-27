/**
 * Command view — Archon's primary control surface.
 *
 * Not a dashboard and not a chat window: one powerful command box, the Archon
 * Core topology, a live instrument strip, and an active-operations list.
 * Commands run through the backend and surface as operations, not chat turns.
 */

import { ArchonCore } from "../components/archon-core.js";
import { executeCommand, systemInfo, describeCapabilities, BackendUnavailable } from "../api.js";
import { el, panel, sectionLabel, kv, button } from "../ui.js";
import { showPage } from "../router.js";

interface Operation {
  title: string;
  command: string;
  state: "running" | "done" | "failed";
  route: string;
  detail: string;
}

const ROUTE_HINTS: [string[], string][] = [
  [["build", "iso", "distro", "kernel", "os "], "BUILD"],
  [["workflow", "n8n", "automat"], "AUTOMATION"],
  [["deploy", "kubernetes", "k8s", "cluster", "cloud", "server"], "CLOUD"],
  [["analyz", "dataset", "telemetry", "query", "data"], "DATA"],
  [["remember", "prefer", "memory"], "MEMORY"],
  [["model", "route", "reason"], "AI"],
  [["system", "process", "cpu", "disk", "hardware", "file"], "SYSTEMS"],
];

function routeFor(text: string): string {
  const low = text.toLowerCase();
  for (const [keys, name] of ROUTE_HINTS) if (keys.some((k) => low.includes(k))) return name;
  return "AI";
}

const PLACEHOLDER =
  "Build me a personalized Arch Linux environment for cybersecurity and AI development…";

// Module-level handles so the top bar / palette can hand a command to this view.
const operations: Operation[] = [];
let core: ArchonCore | null = null;
let opsList: HTMLElement | null = null;
let inputEl: HTMLTextAreaElement | null = null;
let opsCounter: { set: (v: string, c?: string) => void } | null = null;

export function renderCommand(root: HTMLElement): () => void {
  const layout = el("div", { class: "command-layout" });

  // ── Left: command box + operations ──────────────────────────────────────
  const left = el("div", { class: "command-left" });
  left.append(el("h1", { class: "command-heading", text: "WHAT DO YOU WANT TO ACCOMPLISH?" }));

  inputEl = el("textarea", {
    class: "command-input",
    placeholder: PLACEHOLDER,
    rows: 3,
  }) as HTMLTextAreaElement;
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submit();
    }
  });

  const execBtn = button("EXECUTE  →", "primary", submit);
  const box = el("div", { class: "command-box" }, [
    inputEl,
    el("div", { class: "command-bar" }, [
      el("div", { class: "command-chips" }, [
        chip("Capabilities", "mcp"),
        chip("Target system", "systems"),
      ]),
      execBtn,
    ]),
  ]);
  left.append(box);

  left.append(sectionLabel("Active Operations"));
  opsList = el("div", { class: "ops-list" });
  left.append(opsList);
  renderOps();

  // ── Right: core + instruments ───────────────────────────────────────────
  const right = el("div", { class: "command-right" });

  const corePanel = panel("Archon Core");
  const coreHost = el("div", { class: "core-host" });
  corePanel.body.append(coreHost);
  core = new ArchonCore();
  coreHost.append(core.canvas);
  core.start();
  right.append(corePanel.root);

  const statusPanel = panel("System Status");
  const kvs = {
    core: kv("Core", "● ONLINE"),
    cpu: kv("CPU"),
    ram: kv("RAM"),
    disk: kv("Disk"),
    caps: kv("Capabilities"),
    ops: kv("Operations", "0"),
  };
  kvs.core.set("● ONLINE", "var(--success)");
  opsCounter = kvs.ops;
  for (const k of Object.values(kvs)) statusPanel.body.append(k.row);
  right.append(statusPanel.root);

  layout.append(left, right);
  root.append(layout);

  // Live instruments.
  const refresh = async () => {
    try {
      const s = await systemInfo();
      kvs.cpu.set(`${s.cpu_usage.toFixed(0)}%`);
      kvs.ram.set(`${((s.mem_used / s.mem_total) * 100).toFixed(0)}%`);
      const root_disk = s.disks.find((d) => d.mount === "/") ?? s.disks[0];
      if (root_disk) {
        const used = ((root_disk.total - root_disk.available) / root_disk.total) * 100;
        kvs.disk.set(`${used.toFixed(0)}%`);
      }
    } catch (err) {
      const unavailable = err instanceof BackendUnavailable;
      kvs.core.set(unavailable ? "● OFFLINE" : "● DEGRADED", "var(--error)");
      kvs.cpu.set("—");
      kvs.ram.set("—");
      kvs.disk.set("—");
    }
  };
  describeCapabilities()
    .then((c) => kvs.caps.set(String(Object.keys(c).length)))
    .catch(() => kvs.caps.set("—"));
  refresh();
  const timer = window.setInterval(refresh, 2500);

  return () => {
    window.clearInterval(timer);
    core?.stop();
    core = null;
    opsList = null;
    inputEl = null;
    opsCounter = null;
  };
}

/** Public hook: run a command in this view (from the top bar / palette). */
export function runCommand(text: string): void {
  if (inputEl) inputEl.value = text;
  submit();
}

function submit(): void {
  const text = (inputEl?.value ?? "").trim();
  if (!text) return;
  if (inputEl) inputEl.value = "";

  const op: Operation = {
    title: text.length > 60 ? text.slice(0, 60) + "…" : text,
    command: text,
    state: "running",
    route: routeFor(text),
    detail: "Dispatching…",
  };
  operations.unshift(op);
  core?.setActive(op.route);
  renderOps();

  executeCommand(text)
    .then((res) => {
      const ok = res.success !== false;
      op.state = ok ? "done" : "failed";
      op.detail =
        (res.kind === "conversation" ? res.reply : res.result || res.reply || res.error) ||
        "Complete";
    })
    .catch((err) => {
      op.state = "failed";
      op.detail = err instanceof BackendUnavailable
        ? "Backend unavailable — Archon core is not running."
        : String(err);
    })
    .finally(() => {
      if (!operations.some((o) => o.state === "running")) core?.setActive(null);
      renderOps();
    });
}

function renderOps(): void {
  if (!opsList) return;
  const active = operations.filter((o) => o.state === "running").length;
  opsCounter?.set(String(active), active ? "var(--gold)" : "var(--text-muted)");

  opsList.innerHTML = "";
  if (operations.length === 0) {
    opsList.append(
      el("div", { class: "ops-empty", text: "Archon is standing by. Describe an operation above to begin." }),
    );
    return;
  }
  for (const op of operations.slice(0, 12)) {
    const glyph = op.state === "running" ? "◉" : op.state === "done" ? "✓" : "✕";
    opsList.append(
      el("div", { class: `op-row op-${op.state}` }, [
        el("div", { class: "op-head" }, [
          el("span", { class: "op-glyph", text: glyph }),
          el("span", { class: "op-title", text: op.title }),
          el("span", { class: "op-route", text: op.route }),
        ]),
        el("div", { class: "op-detail", text: op.detail }),
      ]),
    );
  }
}

function chip(label: string, page: string): HTMLElement {
  const b = el("button", { class: "chip", text: label });
  b.addEventListener("click", () => showPage(page as never));
  return b;
}
