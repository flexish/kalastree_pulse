/**
 * Kalastree Pulse — shared client-side entrypoint.
 * Later phases (reflection form, tree animation, admin charts) add their own
 * modules; this file only holds behaviour common to every page.
 */

document.addEventListener("DOMContentLoaded", () => {
  document.body.classList.add("is-ready");
});
