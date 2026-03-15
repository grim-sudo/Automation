/**
 * Toast notification system.
 * Usage: toast.success("Created folder") / toast.error("Failed") / toast.info("…")
 */

type ToastType = "success" | "error" | "info";

function show(message: string, type: ToastType, durationMs = 3000): void {
  const container = document.getElementById("toast-container")!;
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => {
    el.style.transition = "opacity 300ms";
    el.style.opacity = "0";
    setTimeout(() => el.remove(), 320);
  }, durationMs);
}

export const toast = {
  success: (msg: string) => show(msg, "success"),
  error:   (msg: string) => show(msg, "error",   4000),
  info:    (msg: string) => show(msg, "info"),
};
