/** Sparkline — mini SVG line chart for metrics. */

export class Sparkline {
  private svg: SVGSVGElement;
  private path: SVGPathElement;
  private data: number[] = [];
  private maxPoints: number;

  constructor(
    container: HTMLElement,
    maxPoints = 30,
    width = 120,
    height = 36,
    color = "var(--cyan)"
  ) {
    this.maxPoints = maxPoints;

    this.svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    this.svg.setAttribute("width", String(width));
    this.svg.setAttribute("height", String(height));
    this.svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    Object.assign(this.svg.style, { display: "block" });

    // Fill area
    const fillPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    fillPath.setAttribute("fill", "url(#sparkGrad)");
    fillPath.setAttribute("opacity", "0.2");

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const grad = document.createElementNS("http://www.w3.org/2000/svg", "linearGradient");
    grad.setAttribute("id", "sparkGrad");
    grad.setAttribute("x1", "0");
    grad.setAttribute("y1", "0");
    grad.setAttribute("x2", "0");
    grad.setAttribute("y2", "1");
    const stop1 = document.createElementNS("http://www.w3.org/2000/svg", "stop");
    stop1.setAttribute("offset", "0%");
    stop1.setAttribute("stop-color", "#06b6d4");
    const stop2 = document.createElementNS("http://www.w3.org/2000/svg", "stop");
    stop2.setAttribute("offset", "100%");
    stop2.setAttribute("stop-color", "transparent");
    grad.appendChild(stop1);
    grad.appendChild(stop2);
    defs.appendChild(grad);
    this.svg.appendChild(defs);

    this.path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    this.path.setAttribute("fill", "none");
    this.path.setAttribute("stroke", color);
    this.path.setAttribute("stroke-width", "1.5");
    this.path.setAttribute("stroke-linecap", "round");
    this.path.setAttribute("stroke-linejoin", "round");

    this.svg.appendChild(fillPath);
    this.svg.appendChild(this.path);
    container.appendChild(this.svg);
  }

  push(value: number): void {
    this.data.push(value);
    if (this.data.length > this.maxPoints) this.data.shift();
    this.redraw();
  }

  private redraw(): void {
    if (this.data.length < 2) return;
    const w = Number(this.svg.getAttribute("width"));
    const h = Number(this.svg.getAttribute("height"));
    const max = Math.max(...this.data, 1);
    const min = Math.min(...this.data);
    const range = max - min || 1;

    const pts = this.data.map((v, i) => {
      const x = (i / (this.data.length - 1)) * w;
      const y = h - ((v - min) / range) * (h * 0.8) - h * 0.1;
      return `${x},${y}`;
    });

    this.path.setAttribute("d", `M ${pts.join(" L ")}`);
  }
}
