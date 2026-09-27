/**
 * Chat — converse with the Archon intelligence layer. Shows actions and results
 * only; never chain-of-thought. Requests run against the Python core and the
 * input stays responsive while a reply is pending.
 */

import { sendMessage, BackendUnavailable } from "../api.js";
import { el } from "../ui.js";

interface Turn {
  role: "user" | "assistant";
  content: string;
}

const history: Turn[] = [];

export function renderChat(root: HTMLElement): void {
  const wrap = el("div", { class: "chat-view" });
  const log = el("div", { class: "chat-log" });
  const input = el("textarea", {
    class: "chat-input",
    placeholder: "Message Archon…",
    rows: 1,
  }) as HTMLTextAreaElement;
  const send = el("button", { class: "btn btn-primary", text: "Send" });

  const composer = el("div", { class: "chat-composer" }, [input, send]);
  wrap.append(log, composer);
  root.append(wrap);

  const paint = () => {
    log.innerHTML = "";
    for (const t of history) {
      log.append(el("div", { class: `chat-bubble ${t.role}` }, [
        el("div", { class: "bubble-role", text: t.role === "user" ? "You" : "Archon" }),
        el("div", { class: "bubble-body", text: t.content }),
      ]));
    }
    log.scrollTop = log.scrollHeight;
  };
  paint();

  const submit = () => {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    history.push({ role: "user", content: text });
    const pending: Turn = { role: "assistant", content: "…" };
    history.push(pending);
    paint();

    const prior = history.slice(0, -2).map((t) => ({ role: t.role, content: t.content }));
    sendMessage(text, prior)
      .then((res) => {
        pending.content = res.reply || res.result || res.error || "(no reply)";
      })
      .catch((err) => {
        pending.content =
          err instanceof BackendUnavailable
            ? "Backend unavailable — Archon core is not running."
            : String(err);
      })
      .finally(paint);
  };

  send.addEventListener("click", submit);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  });
}
