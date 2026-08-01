/**
 * Kalastree Pulse — dark/light mode toggle.
 * The initial theme is set synchronously by an inline script in
 * base.html's <head> (before paint, to avoid a flash); this only handles
 * the toggle button's click and keeping the icon in sync.
 */

const THEME_STORAGE_KEY = "kalastree-theme";

function currentTheme() {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

function applyIcon(button) {
  const icon = button.querySelector(".theme-toggle__icon");
  if (icon) icon.textContent = currentTheme() === "dark" ? "☀️" : "🌙";
}

document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("theme-toggle");
  if (!button) return;

  applyIcon(button);

  button.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(THEME_STORAGE_KEY, next);
    applyIcon(button);
  });
});
