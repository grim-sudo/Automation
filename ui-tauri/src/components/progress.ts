/** Animated progress bar component. */

export class ProgressBar {
  private el: HTMLElement;
  private fill: HTMLElement;
  private label: HTMLElement;
  private pct = 0;

  constructor(container: HTMLElement, title?: string) {
    this.el = document.createElement("div");
    this.el.style.width = "100%";

    if (title) {
      const header = document.createElement("div");
      Object.assign(header.style, {
        display: "flex",
        justifyContent: "space-between",
        marginBottom: "6px",
      });
      const t = document.createElement("span");
      t.textContent = title;
      t.style.fontSize = "var(--font-size-small)";
      t.style.color = "var(--text-secondary)";

      this.label = document.createElement("span");
      Object.assign(this.label.style, {
        fontSize: "var(--font-size-small)",
        color: "var(--text-accent)",
      });
      this.label.textContent = "0%";

      header.appendChild(t);
      header.appendChild(this.label);
      this.el.appendChild(header);
    } else {
      this.label = document.createElement("span");
    }

    const track = document.createElement("div");
    Object.assign(track.style, {
      width: "100%",
      height: "6px",
      background: "var(--bg-raised)",
      borderRadius: "3px",
      overflow: "hidden",
    });

    this.fill = document.createElement("div");
    Object.assign(this.fill.style, {
      height: "100%",
      width: "0%",
      background: "linear-gradient(90deg, var(--purple), var(--cyan))",
      borderRadius: "3px",
      transition: "width var(--anim-normal) ease",
    });

    track.appendChild(this.fill);
    this.el.appendChild(track);
    container.appendChild(this.el);
  }

  setProgress(pct: number): void {
    this.pct = Math.max(0, Math.min(100, pct));
    this.fill.style.width = `${this.pct}%`;
    if (this.label) this.label.textContent = `${Math.round(this.pct)}%`;
  }

  /** Animate an indeterminate shimmer. Returns a stop function. */
  startIndeterminate(): () => void {
    let x = 0;
    let dir = 1;
    const id = setInterval(() => {
      x += dir * 2;
      if (x >= 80) dir = -1;
      if (x <= 0)  dir = 1;
      this.fill.style.width = "20%";
      this.fill.style.marginLeft = `${x}%`;
    }, 20);
    return () => {
      clearInterval(id);
      this.fill.style.marginLeft = "0";
    };
  }
}
