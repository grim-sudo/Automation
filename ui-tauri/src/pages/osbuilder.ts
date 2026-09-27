/**
 * OS Builder — compose and build a custom Linux image. Lists the real distro
 * profiles from the Archon core. The actual build runs via the CLI (the IPC
 * bridge intentionally does not spawn long builds), which we state plainly.
 */

import { distroListProfiles, BackendUnavailable } from "../api.js";
import { el, panel, emptyState, sectionLabel } from "../ui.js";

export function renderOsBuilder(root: HTMLElement): void {
  const wrap = el("div", { class: "page-pad" });
  root.append(wrap);

  const p = panel("Profiles", { subtitle: "Distro definitions Archon can build from" });
  wrap.append(p.root);

  distroListProfiles()
    .then((profiles) => {
      if (!profiles.length) {
        p.body.append(
          emptyState({
            glyph: "🐧",
            title: "No profiles",
            message: "No distro profiles were found in the core.",
            state: "REAL",
          }),
        );
        return;
      }
      const list = el("div", { class: "profile-list" });
      for (const name of profiles) {
        list.append(
          el("div", { class: "profile-item" }, [
            el("span", { class: "profile-glyph", text: "🐧" }),
            el("span", { class: "profile-name", text: String(name) }),
          ]),
        );
      }
      p.body.append(list);
      p.body.append(sectionLabel("Building"));
      p.body.append(
        el("div", {
          class: "note",
          text: "Image builds are long-running and run through the CLI: `archon distro build <profile>`. The GUI lists and inspects profiles; it does not block on a build.",
        }),
      );
    })
    .catch((err) => {
      p.body.append(
        emptyState({
          glyph: "🐧",
          title: "Profiles unavailable",
          message:
            err instanceof BackendUnavailable
              ? "Distro profiles come from the Archon core. Run Archon as a desktop app to see them."
              : String(err),
          state: "UNAVAILABLE",
        }),
      );
    });
}
