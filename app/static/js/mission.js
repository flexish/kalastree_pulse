/**
 * Kalastree Pulse — Mission Dashboard entrance animations.
 * Count-up numbers and an animated progress-bar fill; both jump straight
 * to their final value under prefers-reduced-motion rather than skipping
 * silently, so the real number is never missing, just not animated.
 */

function animateCountUp(el, target, duration) {
  const start = performance.now();

  function frame(now) {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(eased * target).toLocaleString();
    if (progress < 1) requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
}

document.addEventListener("DOMContentLoaded", () => {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  document.querySelectorAll("[data-countup]").forEach((el) => {
    const target = Number(el.dataset.target) || 0;
    if (prefersReducedMotion) {
      el.textContent = target.toLocaleString();
      return;
    }
    animateCountUp(el, target, 1200);
  });

  document.querySelectorAll("[data-progress-fill]").forEach((el) => {
    const targetWidth = el.dataset.targetWidth || "0";
    if (prefersReducedMotion) {
      el.style.width = `${targetWidth}%`;
      return;
    }
    requestAnimationFrame(() => {
      el.style.transition = "width 1.2s ease-out";
      el.style.width = `${targetWidth}%`;
    });
  });
});
