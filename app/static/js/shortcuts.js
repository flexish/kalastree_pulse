/**
 * Kalastree Pulse — global keyboard shortcuts.
 * Only loaded on pages where the visitor is signed in (base.html gates
 * the <script> tag itself). Ignored while typing in a form field so
 * shortcuts never fight with entering a reflection or a search term.
 */

const SHORTCUTS = [
  { key: "d", label: "Go to Dashboard", href: "/" },
  { key: "r", label: "Start Reflection", href: "/reflection" },
  { key: "m", label: "Go to Mission", href: "/mission" },
  { key: "g", label: "Go to Growth", href: "/growth" },
  { key: "a", label: "Go to Admin", href: "/admin" },
];

function isTyping() {
  const el = document.activeElement;
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || el.isContentEditable;
}

function buildHelpOverlay() {
  const overlay = document.createElement("div");
  overlay.className = "shortcuts-overlay";
  overlay.id = "shortcuts-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-label", "Keyboard shortcuts");
  overlay.hidden = true;

  const card = document.createElement("div");
  card.className = "shortcuts-overlay__card glass";

  const title = document.createElement("h2");
  title.textContent = "Keyboard shortcuts";
  card.appendChild(title);

  const list = document.createElement("ul");
  list.className = "shortcuts-overlay__list";

  SHORTCUTS.forEach(({ key, label }) => {
    const item = document.createElement("li");
    const kbd = document.createElement("kbd");
    kbd.textContent = key;
    const span = document.createElement("span");
    span.textContent = label;
    item.append(kbd, span);
    list.appendChild(item);
  });

  const closeItem = document.createElement("li");
  const closeKbd = document.createElement("kbd");
  closeKbd.textContent = "Esc";
  const closeSpan = document.createElement("span");
  closeSpan.textContent = "Close this";
  closeItem.append(closeKbd, closeSpan);
  list.appendChild(closeItem);

  card.appendChild(list);
  overlay.appendChild(card);

  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) overlay.hidden = true;
  });

  document.body.appendChild(overlay);
  return overlay;
}

document.addEventListener("DOMContentLoaded", () => {
  const overlay = buildHelpOverlay();

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      overlay.hidden = true;
      return;
    }

    if (isTyping() || event.metaKey || event.ctrlKey || event.altKey) return;

    if (event.key === "?") {
      overlay.hidden = !overlay.hidden;
      return;
    }

    if (!overlay.hidden) return;

    const shortcut = SHORTCUTS.find((s) => s.key === event.key.toLowerCase());
    if (shortcut) {
      window.location.href = shortcut.href;
    }
  });
});
