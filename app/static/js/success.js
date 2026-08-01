/**
 * Kalastree Pulse — reflection success screen.
 * Confetti is purely celebratory and skipped entirely if the visitor
 * prefers reduced motion; the tree's grow-in animation is handled by CSS
 * and gets the same guard there.
 */

const CONFETTI_COLORS = ["#22c55e", "#16a34a", "#6366f1", "#f59e0b", "#ef4444"];
const CONFETTI_COUNT = 70;

function launchConfetti(container) {
  for (let i = 0; i < CONFETTI_COUNT; i++) {
    const piece = document.createElement("span");
    piece.className = "confetti-piece";
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.backgroundColor = CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)];
    piece.style.setProperty("--rotate", `${Math.random() * 360}deg`);
    piece.style.setProperty("--x-drift", `${Math.random() * 160 - 80}px`);
    piece.style.setProperty("--duration", `${2 + Math.random() * 1.5}s`);
    piece.style.setProperty("--delay", `${Math.random() * 0.5}s`);
    container.appendChild(piece);
    piece.addEventListener("animationend", () => piece.remove());
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (prefersReducedMotion) return;

  const layer = document.getElementById("confetti-layer");
  if (layer) launchConfetti(layer);
});
