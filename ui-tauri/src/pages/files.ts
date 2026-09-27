/**
 * Files — read-only local filesystem browser backed by the Rust `list_dir`
 * command. Never writes; clicking a directory navigates into it.
 */

import { listDir, BackendUnavailable, type DirListing } from "../api.js";
import { el, panel, emptyState, formatBytes } from "../ui.js";

export function renderFiles(root: HTMLElement): void {
  const wrap = el("div", { class: "page-pad" });
  root.append(wrap);

  const pathBar = el("div", { class: "path-bar", text: "…" });
  const p = panel("Filesystem", { subtitle: "Read-only" });
  p.body.append(pathBar);
  const host = el("div", { class: "table-scroll file-list" });
  p.body.append(host);
  wrap.append(p.root);

  const load = (path?: string) => {
    listDir(path)
      .then((d) => paint(d))
      .catch((err) => {
        wrap.replaceChildren(
          emptyState({
            glyph: "⚠",
            title: "Filesystem unavailable",
            message:
              err instanceof BackendUnavailable
                ? "The file browser is served by the Rust shell. Run Archon as a desktop app to browse files."
                : String(err),
            state: "UNAVAILABLE",
          }),
        );
      });
  };

  const paint = (d: DirListing) => {
    pathBar.textContent = d.path;
    host.innerHTML = "";
    if (d.parent) {
      host.append(fileRow("↑", "..", true, () => load(d.parent!)));
    }
    for (const e of d.entries) {
      host.append(
        fileRow(
          e.is_dir ? "▸" : "·",
          e.name + (e.is_dir ? "/" : ""),
          e.is_dir,
          e.is_dir ? () => load(e.path) : undefined,
          e.is_dir ? "" : formatBytes(e.size),
        ),
      );
    }
  };

  load();
}

function fileRow(
  glyph: string,
  name: string,
  isDir: boolean,
  onClick?: () => void,
  size = "",
): HTMLElement {
  const row = el("div", { class: `file-row${isDir ? " is-dir" : ""}` }, [
    el("span", { class: "file-glyph", text: glyph }),
    el("span", { class: "file-name", text: name }),
    el("span", { class: "file-size", text: size }),
  ]);
  if (onClick) row.addEventListener("click", onClick);
  return row;
}
