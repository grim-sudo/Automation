/**
 * Chat page — streaming AI conversation.
 * Mirrors archon/ui/gui/pages/chat_page.py.
 */

import { invoke } from "@tauri-apps/api/core";
import { toast }  from "../components/toast.js";

interface Message { role: "user" | "assistant"; content: string; }

const history: Message[] = [];

export function renderChat(container: HTMLElement): void {
  container.innerHTML = `
    <div class="topbar">
      <span class="topbar-title">💬  AI Chat</span>
      <div class="topbar-spacer"></div>
      <button class="btn btn-ghost" id="clear-chat">✕ Clear</button>
    </div>
    <div id="chat-messages" style="flex:1;overflow-y:auto;padding:16px;
         display:flex;flex-direction:column;gap:10px;"></div>
    <div style="padding:12px 16px;border-top:1px solid var(--border-subtle);
         background:var(--bg-surface);display:flex;gap:8px;">
      <input id="chat-input" type="text" placeholder="Ask anything or describe a task…"
             style="flex:1;" />
      <button class="btn btn-primary" id="chat-send">Send</button>
    </div>
  `;

  const messagesEl = container.querySelector<HTMLElement>("#chat-messages")!;
  const input      = container.querySelector<HTMLInputElement>("#chat-input")!;
  const sendBtn    = container.querySelector<HTMLButtonElement>("#chat-send")!;

  function appendBubble(role: "user" | "assistant", text: string): HTMLElement {
    const wrap = document.createElement("div");
    wrap.style.display = "flex";
    wrap.style.justifyContent = role === "user" ? "flex-end" : "flex-start";
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;
    bubble.textContent = text;
    wrap.appendChild(bubble);
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return bubble;
  }

  async function sendMessage(): Promise<void> {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendBtn.disabled = true;

    history.push({ role: "user", content: text });
    appendBubble("user", text);

    const thinkingBubble = appendBubble("assistant", "…");
    try {
      const response = await invoke<string>("send_message", {
        message: text,
        history: history.slice(-10),
      });
      thinkingBubble.textContent = response;
      history.push({ role: "assistant", content: response });
    } catch (err) {
      thinkingBubble.textContent = `⚠  ${err}`;
      thinkingBubble.style.color = "var(--error)";
      toast.error(String(err));
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  container.querySelector("#clear-chat")!.addEventListener("click", () => {
    history.length = 0;
    messagesEl.innerHTML = "";
  });

  // Welcome message
  appendBubble("assistant", "Hi! I'm Archon. Describe a task or ask anything.");
}
