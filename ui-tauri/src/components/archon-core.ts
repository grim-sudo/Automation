/**
 * ArchonCore — the central-intelligence topology.
 *
 * One central ARCHON node orbited by subsystem nodes on thin steel rules. Gold
 * marks an active connection and a signal travels that edge while a subsystem
 * is being invoked. Restrained: a slow quiet orbit, not a spinning reactor.
 * Pure canvas, driven by requestAnimationFrame; call `stop()` to release it.
 */

const SUBSYSTEMS = ["AI", "SYSTEMS", "AUTOMATION", "MCP", "DATA", "BUILD", "CLOUD", "MEMORY"];

const COL = {
  gold: "#d6a84f",
  goldLight: "#f0c96a",
  edge: "#2b3a44",
  bg: "#0e1114",
  surface: "#14181c",
  border: "#30373d",
  textAccent: "#f0c96a",
  textMuted: "#73787b",
  textPrimary: "#eceae5",
};

export class ArchonCore {
  readonly canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private names: string[];
  private phase = 0;
  private signal = 0;
  private active: string | null = null;
  private raf = 0;
  private running = false;

  constructor(names: string[] = SUBSYSTEMS) {
    this.names = names;
    this.canvas = document.createElement("canvas");
    this.canvas.className = "archon-core";
    this.ctx = this.canvas.getContext("2d")!;
  }

  setActive(name: string | null) {
    this.active = name;
    this.signal = 0;
  }

  start() {
    if (this.running) return;
    this.running = true;
    const loop = () => {
      if (!this.running) return;
      this.phase += 0.004;
      if (this.active) this.signal = (this.signal + 0.03) % 1;
      this.draw();
      this.raf = requestAnimationFrame(loop);
    };
    loop();
  }

  stop() {
    this.running = false;
    cancelAnimationFrame(this.raf);
  }

  private draw() {
    const c = this.canvas;
    const parent = c.parentElement;
    if (!parent) return;
    const dpr = window.devicePixelRatio || 1;
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    if (c.width !== w * dpr || c.height !== h * dpr) {
      c.width = w * dpr;
      c.height = h * dpr;
      c.style.width = `${w}px`;
      c.style.height = `${h}px`;
    }
    const ctx = this.ctx;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) * 0.36;
    const n = this.names.length;
    const nodes = this.names.map((name, i) => {
      const ang = this.phase + (Math.PI * 2 * i) / n - Math.PI / 2;
      return { x: cx + radius * Math.cos(ang), y: cy + radius * Math.sin(ang), name };
    });

    // Connections.
    for (const nd of nodes) {
      const on = nd.name === this.active;
      ctx.strokeStyle = on ? COL.gold : COL.edge;
      ctx.lineWidth = on ? 2 : 1;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(nd.x, nd.y);
      ctx.stroke();
    }

    // Traveling signal.
    if (this.active) {
      const nd = nodes.find((x) => x.name === this.active);
      if (nd) {
        const sx = cx + (nd.x - cx) * this.signal;
        const sy = cy + (nd.y - cy) * this.signal;
        ctx.fillStyle = COL.goldLight;
        ctx.beginPath();
        ctx.arc(sx, sy, 4, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Subsystem nodes.
    ctx.font = "700 8px Inter, sans-serif";
    ctx.textAlign = "center";
    for (const nd of nodes) {
      const on = nd.name === this.active;
      ctx.fillStyle = on ? COL.gold : COL.surface;
      ctx.strokeStyle = on ? COL.gold : COL.border;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(nd.x, nd.y, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = on ? COL.textAccent : COL.textMuted;
      ctx.fillText(nd.name, nd.x, nd.y + 16);
    }

    // Central ARCHON node — diamond with soft halo.
    const coreR = Math.max(10, Math.min(w, h) * 0.055);
    const grad = ctx.createRadialGradient(cx, cy, coreR, cx, cy, coreR * 2.6);
    grad.addColorStop(0, "rgba(214,168,79,0.16)");
    grad.addColorStop(1, "rgba(214,168,79,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, coreR * 2.6, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = COL.surface;
    ctx.strokeStyle = COL.gold;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, coreR, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    const d = coreR * 0.5;
    ctx.fillStyle = COL.gold;
    ctx.beginPath();
    ctx.moveTo(cx, cy - d);
    ctx.lineTo(cx + d, cy);
    ctx.lineTo(cx, cy + d);
    ctx.lineTo(cx - d, cy);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = COL.textPrimary;
    ctx.font = "700 9px Inter, sans-serif";
    ctx.fillText("ARCHON", cx, cy + coreR + 16);
  }
}
